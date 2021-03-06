angular.module("services.page", [
  'signup'
])
angular.module("services.page")
  .factory("Page", function($location,
                            $rootScope,
                            security,
                            ProfileAboutService,
                            KeyMetrics,
                            KeyProducts,
                            Loading,
                            ProfileProducts){
    var title = '';
    var notificationsLoc = "header"
    var lastScrollPosition = {}
    var isEmbedded =  _($location.path()).startsWith("/embed/")
    var profileUrl
    var pageName
    var isInfopage
    var profileSlug

    var nonProfilePages = [
      "/",
      "/reset-password",
      "/h-index",
      "/open-science",
      "/faq",
      "/legal",
      "/metrics",
      "/signup",
      "/about",
      "/advisors",
      "/spread-the-word",
      "/buy-subscriptions"
    ]

    var profileServices = [
      ProfileAboutService,
      ProfileProducts,
      KeyProducts,
      KeyMetrics
    ]


    $rootScope.$on('$routeChangeSuccess', function () {
      isInfopage = false // init...it's being set elsewhere
      pageName = null // init...it's being set elsewhere

      profileSlug = findProfileSlug()

      if (!profileSlug) {
        _.each(profileServices, function(service){
          service.clear()
        })
      }

      handleDeadProfile(ProfileAboutService, profileSlug)

      ProfileAboutService.handleSlug(profileServices, profileSlug).then(function(resp){
          handleDeadProfile(ProfileAboutService, profileSlug)
        }
      )
    });



    function handleDeadProfile(ProfileAboutService, profileSlug){
      if (ProfileAboutService.data.is_live === false){
        console.log("we've got a dead profile.")
        Loading.finishPage()

        ProfileProducts.clear()
        KeyProducts.clear()
        KeyMetrics.clear()

        // is this profile's owner here? give em a chance to subscribe.
        if (security.getCurrentUserSlug() == profileSlug){
          $location.path("/settings/subscription")
        }

        // for everyone else, show a Dead Profile page
        else {
          var searchParams = $location.search()
          if (searchParams && searchParams.show_expired ) {
            console.log("overriding the expired page, showing everything.")
          }
          $location.path(profileSlug + "/expired")

        }
      }
    }


    function findProfileSlug(){
      var firstPartOfPath = "/" + $location.path().split("/")[1]
      if (firstPartOfPath == "/settings") {
        console.log("findprofileslug reporting /settings page")
        return security.getCurrentUserSlug()
      }

      if (_.contains(nonProfilePages, firstPartOfPath)){
        return undefined
      }
      else {
        return firstPartOfPath.substr(1) // no slash
      }
    }

    var isSubscriptionPage = function(){
      var splitPath = $location.path().split("/")
      return splitPath[1] == "settings" && splitPath[2] == "subscription"

    }





    var getPageType = function(){
      // no longer maintained...i think/hope no longer used
      // as of Oct 16 2014

      var myPageType = "profile"
      var path = $location.path()

      var settingsPages = [
        "/settings",
        "/reset-password"
      ]

      var infopages = [
        "/faq",
        "/about"
      ]

      if (path === "/"){
        myPageType = "landing"
      }
      else if (path === "/CarlBoettiger") {
        myPageType = "demoProfile"
      }
      else if (path === "/signup") {
        myPageType = "signup"
      }
      else if (_.contains(infopages, path)){
        myPageType = "infopages"
      }
      else if (_.contains(settingsPages, path)) {
        myPageType = "settings"
      }
      else if (path.indexOf("products/add") > -1) {
        myPageType = "importIndividual"
      }
      else if (path.indexOf("account") > -1) {
        myPageType = "linkAccount"
      }

      return myPageType
    }


    return {


      setProfileUrl: function(url){
        profileUrl = url
      },
      getProfileUrl: function(){
        return profileUrl
      },

      getUrl: function(){
        return window.location.href
      },


      'setNotificationsLoc': function(loc){
        notificationsLoc = loc;
      },
      showNotificationsIn: function(loc){
        return notificationsLoc == loc
      },
      setVersion: function(versionName){
        version = versionName;
      },
      getBodyClasses: function(){
        var conditionalClasses = {
          'embedded': isEmbedded
        }

        var classes = [
          "page-name-" + pageName
        ]

        _.each(conditionalClasses, function(v, k){
          if (v) classes.push(k)
        })

        return classes.join(" ")



      },
      isInfopage: function(){
        return !!isInfopage
      },
      setInfopage: function(val){
        isInfopage = !!val
      },

      'isEmbedded': function(){
        return isEmbedded
      } ,

      getTitle: function() { return title; },
      setTitle: function(newTitle) { title = "Impactstory: " + newTitle },


      isProfilePage:function(){
        var path = $location.path()
        return (!_.contains(nonProfilePages, path))
      },

      setName: function(name){
        pageName = name
      },

      getUrlSlug: function(){
        return profileSlug
      },

      isNamed: function(name){
        return name === pageName
      },

      setLastScrollPosition: function(pos, path){
        if (pos) {
          lastScrollPosition[path] = pos
        }
      },
      getLastScrollPosition: function(path){
        return lastScrollPosition[path]
      },

      findProfileSlug: findProfileSlug,
      isOnMobile:function(){
        return $rootScope.isOnMobile()
      },

      sendPageloadToSegmentio: function(){

        analytics.page(
          getPageType(),
          $location.path(),
          {
            "viewport width": $(window).width(),
            "page_type": getPageType()
          }
        )
      }
    };
  })












