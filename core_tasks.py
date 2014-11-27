import time 
import os
import json
import logging
import datetime
import random
import celery
import requests
from celery.decorators import task
from celery.signals import task_postrun, task_prerun, task_failure, worker_process_init
from celery import group, chain, chord
from celery import current_app as celery_app
from celery.signals import task_sent
from celery.utils import uuid
from eventlet import timeout

from totalimpact import item as item_module
from totalimpact import db
from totalimpact import REDIS_MAIN_DATABASE_NUMBER
from totalimpact import tiredis, default_settings
from totalimpact.providers.provider import ProviderFactory, ProviderError, ProviderTimeout

from totalimpactwebapp.product import add_product_embed_markup

import rate_limit

logger = logging.getLogger("core.core_tasks")
myredis = tiredis.from_url(os.getenv("REDIS_URL"), db=REDIS_MAIN_DATABASE_NUMBER)

rate = rate_limit.RateLimiter(redis_url=os.getenv("REDIS_URL"), redis_db=REDIS_MAIN_DATABASE_NUMBER)
rate.add_condition({'requests':25, 'seconds':1})


# from https://github.com/celery/celery/issues/1671#issuecomment-47247074
# pending this being fixed in useful celery version
"""
Monkey patch for celery.chord.type property
"""
def _type(self):
    if self._type:
        return self._type
    if self._app:
        app = self._app
    else:
        try:
            app = self.tasks[0].type.app
        except (IndexError, AttributeError):
            app = self.body.type.app
    return app.tasks['celery.chord']
from celery import canvas
canvas.chord.type = property(_type)
#### end monkeypatch


@task_postrun.connect()
def task_postrun_handler(*args, **kwargs):    
    db.session.remove()


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, args=None, kwargs=None, exception=None, traceback=None, einfo=None, **kwds):
    try:
        logger.error(u"Celery task FAILED on task_id={task_id}, {exception}, {traceback}, {einfo}, {args}".format(
            task_id=task_id, args=args, exception=exception, einfo=einfo))
    except KeyError:
        pass




def provider_method_wrapper(tiid, input_aliases_dict, provider, method_name):

    # logger.info(u"{:20}: in provider_method_wrapper with {tiid} {provider_name} {method_name} with {aliases}".format(
    #    "wrapper", tiid=tiid, provider_name=provider.provider_name, method_name=method_name, aliases=input_aliases_dict))

    provider_name = provider.provider_name
    worker_name = provider_name+"_worker"

    if isinstance(input_aliases_dict, list):
        input_aliases_dict = item_module.alias_dict_from_tuples(input_aliases_dict)    

    input_alias_tuples = item_module.alias_tuples_from_dict(input_aliases_dict)
    method = getattr(provider, method_name)

    try:
        method_response = method(input_alias_tuples)
    except ProviderError, e:
        method_response = None

        logger.info(u"{:20}: **ProviderError {tiid} {method_name} {provider_name}, Exception type {exception_type} {exception_arguments}".format(
            worker_name, 
            tiid=tiid, 
            provider_name=provider_name.upper(), 
            method_name=method_name.upper(), 
            exception_type=type(e).__name__, 
            exception_arguments=e.args))

    logger.info(u"{:20}: /biblio_print, RETURNED {tiid} {method_name} {provider_name} : {method_response}".format(
        worker_name, tiid=tiid, method_name=method_name.upper(), 
        provider_name=provider_name.upper(), method_response=method_response))

    if method_name == "aliases" and method_response:
        initial_alias_dict = item_module.alias_dict_from_tuples(method_response)
        new_canonical_aliases_dict = item_module.canonical_aliases(initial_alias_dict)
        full_aliases_dict = item_module.merge_alias_dicts(new_canonical_aliases_dict, input_aliases_dict)
    else:
        full_aliases_dict = input_aliases_dict

    add_to_database_if_nonzero(tiid, method_response, method_name, provider_name)

    return full_aliases_dict




# last variable is an artifact so it has same call signature as other callbacks
def add_to_database_if_nonzero( 
        tiid, 
        new_content, 
        method_name, 
        provider_name):

    if new_content:
        # don't need item with metrics for this purpose, so don't bother getting metrics from db

        item_obj = item_module.Item.query.get(tiid)

        if item_obj:
            if method_name=="aliases":
                if isinstance(new_content, list):
                    new_content = item_module.alias_dict_from_tuples(new_content)    
                item_obj = item_module.add_aliases_to_item_object(new_content, item_obj)
            elif method_name=="biblio":
                updated_item_doc = item_module.update_item_with_new_biblio(new_content, item_obj, provider_name)
            elif method_name=="metrics":
                for metric_name in new_content:
                    item_obj = item_module.add_metric_to_item_object(metric_name, new_content[metric_name], item_obj)
            else:
                logger.warning(u"ack, supposed to save something i don't know about: " + str(new_content))

    return


def sniffer(item_aliases, provider_config=default_settings.PROVIDERS):

    (genre, host) = item_module.decide_genre(item_aliases)

    all_metrics_providers = [provider.provider_name for provider in 
                    ProviderFactory.get_providers(provider_config, "metrics")]

    if (genre == "article") and (host != "arxiv"):
        run = [[("aliases", provider)] for provider in ["mendeley", "crossref", "pubmed", "altmetric_com"]]
        run += [[("biblio", provider) for provider in ["crossref", "pubmed", "mendeley", "webpage"]]]
        run += [[("metrics", provider) for provider in all_metrics_providers]]
    elif (host == "arxiv") or ("doi" in item_aliases):
        run = [[("aliases", provider)] for provider in [host, "altmetric_com"]]
        run += [[("biblio", provider) for provider in [host, "mendeley"]]]
        run += [[("metrics", provider) for provider in all_metrics_providers]]
    else:
        # relevant alias and biblio providers are always the same
        relevant_providers = [host]
        if relevant_providers == ["unknown"]:
            relevant_providers = ["webpage"]
        run = [[("aliases", provider)] for provider in relevant_providers]
        run += [[("biblio", provider) for provider in relevant_providers]]
        run += [[("metrics", provider) for provider in all_metrics_providers]]

    return(run)



@task(priority=0)
def chain_dummy(first_arg, **kwargs):
    try:
        response = first_arg[0]
    except KeyError:
        response = first_arg

    return response


@task()
def provider_run(aliases_dict, tiid, method_name, provider_name):

    provider = ProviderFactory.get_provider(provider_name)

    # logger.info(u"in provider_run for {provider}".format(
    #    provider=provider.provider_name))

    (success, estimated_wait_seconds) = rate.acquire(provider_name, block=False)
    # add up to random 2 seconds to spread it out
    estimated_wait_seconds += random.random() * 3
    if not success:
        logger.warning(u"RATE LIMIT HIT in provider_run for {provider} {method_name} {tiid}, retrying".format(
           provider=provider.provider_name, method_name=method_name, tiid=tiid))
        provider_run.retry(args=[aliases_dict, tiid, method_name, provider_name],
                countdown=estimated_wait_seconds, 
                max_retries=10)

    timeout_seconds = 30
    try:
        with timeout.Timeout(timeout_seconds):
            response = provider_method_wrapper(tiid, aliases_dict, provider, method_name)

    except timeout.Timeout:
        msg = u"TIMEOUT in provider_run for {provider} {method_name} {tiid} after {timeout_seconds} seconds".format(
           provider=provider.provider_name, method_name=method_name, tiid=tiid, timeout_seconds=timeout_seconds)
        # logger.warning(msg)  # message is written elsewhere
        raise ProviderTimeout(msg)

    return response



@task(priority=0)
def after_refresh_complete(tiid, task_ids):
    logger.info(u"here in after_refresh_complete with {tiid}".format(
        tiid=tiid))

    item_obj = item_module.Item.query.get(tiid)

    if item_obj:
        add_product_embed_markup(item_obj.tiid)
        item_obj.set_last_refresh_finished(myredis)
        db.session.add(item_obj)
        db.session.commit()




@task()
def refresh_tiid(tiid, aliases_dict, task_priority):    
    pipeline = sniffer(aliases_dict)
    chain_list = []
    task_ids = []
    for step_config in pipeline:
        group_list = []
        for (method_name, provider_name) in step_config:
            if not chain_list:
                # pass the alias dict in to the first one in the whole chain
                new_task = provider_run.si(aliases_dict, tiid, method_name, provider_name).set(priority=3, queue="core_"+task_priority) #don't start new ones till done
            else:
                new_task = provider_run.s(tiid, method_name, provider_name).set(priority=0, queue="core_"+task_priority)
            uuid_bit = uuid().split("-")[0]
            new_task_id = "task-{tiid}-{method_name}-{provider_name}-{uuid}".format(
                tiid=tiid, method_name=method_name, provider_name=provider_name, uuid=uuid_bit)
            group_list.append(new_task.set(task_id=new_task_id))
            task_ids.append(new_task_id)
        if group_list:
            chain_list.append(group(group_list))
            dummy_name = "DUMMY_{method_name}_{provider_name}".format(
                method_name=method_name, provider_name=provider_name)
            chain_list.append(chain_dummy.s(dummy=dummy_name).set(queue="core_"+task_priority))

    # do this before we kick off the tasks to make sure they are there before tasks finish
    myredis.set_provider_task_ids(tiid, task_ids)

    new_task = after_refresh_complete.si(tiid, task_ids).set(priority=0, queue="core_"+task_priority)
    uuid_bit = uuid().split("-")[0]
    new_task_id = "task-{tiid}-DONE-{uuid}".format(
        tiid=tiid, uuid=uuid_bit)
    chain_list.append(new_task.set(task_id=new_task_id))

    workflow = chain(chain_list)

    # see http://stackoverflow.com/questions/18872854/getting-task-id-inside-a-celery-task
    # workflow_tasks_task.task_id, 
    logger.info(u"before apply_async for tiid {tiid}, refresh_tiids id {task_id}".format(
        tiid=tiid, task_id=refresh_tiid.request.id))

    workflow_apply_async = workflow.apply_async(queue="core_"+task_priority)  

    workflow_tasks = workflow.tasks
    workflow_trackable_task = workflow_tasks[-1]  # see http://blog.cesarcd.com/2014/04/tracking-status-of-celery-chain.html
    workflow_trackable_id = workflow_trackable_task.id

    # see http://stackoverflow.com/questions/18872854/getting-task-id-inside-a-celery-task
    # workflow_tasks_task.task_id, 
    logger.info(u"task id for tiid {tiid}, refresh_tiids id {task_id}, workflow_trackable_id {workflow_trackable_id} task_ids={task_ids}".format(
        tiid=tiid, task_id=refresh_tiid.request.id, workflow_trackable_id=workflow_trackable_id, task_ids=task_ids))

    return workflow_trackable_task


def put_on_celery_queue(tiid, aliases_dict, task_priority="high"):
    logger.info(u"put_on_celery_queue {tiid}".format(
        tiid=tiid))

    #see http://stackoverflow.com/questions/15239880/task-priority-in-celery-with-redis
    if task_priority == "high":
        priority_number = 6
    else:
        priority_number = 9

    refresh_tiid_task = refresh_tiid.apply_async(args=(tiid, aliases_dict, task_priority), 
                                                priority=priority_number, queue="core_"+task_priority)

    return refresh_tiid_task


