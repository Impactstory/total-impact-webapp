angular.module( 'update.update', [
    'emguo.poller',
    'resources.users'
  ])
  .factory("Update", function($modal,
                              $timeout,
                              $q,
                              poller,
                              UsersUpdateStatus){

    var status = {}
    var url_slug
    var modalInstance
    var pollingInterval = 10  // 10ms...as soon as we get server resp, ask again.
    var deferred

    var tick = function(){
      UsersUpdateStatus.get({id:url_slug}).$promise.then(function(resp){
          console.log("tick() got response back from server", resp)
          status = resp
          if (resp.percent_complete == 100){
            console.log("tick() satisfied success criteria, breaking out of recursion loop")
            deferred.resolve("Update finished!")
            modalInstance.close()
          }
          else {
            $timeout(tick, pollingInterval)
          }
        }
      )
    }


    var showUpdateModal = function(url_slug_arg){
      deferred = $q.defer()
      url_slug = url_slug_arg

      UsersUpdateStatus.get({id:url_slug}).$promise.then(
        function(resp) {
          status = resp

          if (status.percent_complete < 100){

            // open the modal
            modalInstance = $modal.open({
              templateUrl: 'update/update-progress.tpl.html',
              controller: 'updateProgressModalCtrl',
              backdrop:"static",
              keyboard: false
            });

            // start polling
            tick()
          }
          else {
            // nothing to see here, this profile is all up to date.
            deferred.reject("Everything is already up to date.")
          }
        }
      )

      return deferred.promise

    }




    return {
      showUpdateModal: showUpdateModal,
      status: status,
      getPercentComplete: function(){
        return status.percent_complete
      },
      getNumComplete: function(){
        return status.num_complete
      },
      getNumUpdating: function() {
        return status.num_updating
      }
    }
  })
  .controller("updateProgressModalCtrl", function($scope, Update){
    $scope.status = Update
  })
