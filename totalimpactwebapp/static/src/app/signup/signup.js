angular.module( 'signup', [
    'services.slug',
    'services.page',
    'resources.users',
    'update.update',
    'security.service',
    'tips',
    'importers.allTheImporters',
    'importers.importer'
    ])
  .factory("Signup", function($location){

    var signupSteps = [
      "name",
      "url",
      "products",
      "password"
    ]


    var getCurrentStep = function(capitalize){
      var ret = "name"
      _.each(signupSteps, function(stepName){

        if ($location.path().indexOf("/"+stepName) > 0){
          ret = stepName
        }
      })

      if (capitalize){
        ret = ret.charAt(0).toUpperCase() + ret.slice(1)
      }

      return ret

    }
    var getIndexOfCurrentStep = function(){
       return _.indexOf(signupSteps, getCurrentStep())
    }

    return {
      signupSteps: function(){
        return signupSteps;
      },
      onSignupStep: function(step){
        return step == getCurrentStep()
        return $location.path().indexOf("/signup/"+step.toLowerCase()) === 0;
      },
      isBeforeCurrentSignupStep: function(stepToCheck) {
        var indexOfStepToCheck = _.indexOf(signupSteps, stepToCheck)
        return getIndexOfCurrentStep() > -1 && indexOfStepToCheck < getIndexOfCurrentStep()
      },
      getTemplatePath: function(){
        return "signup/signup-" + getCurrentStep() + '.tpl.html';
      }
    }
  })

.config(['$routeProvider', function($routeProvider) {

  $routeProvider
    .when('/signup/:url_slug/products/add', {
              templateUrl: 'signup/signup.tpl.html',
              controller: 'signupCtrl',
              resolve:{
              userOwnsThisProfile: function(security){
                return security.testUserAuthenticationLevel("ownsThisProfile")
              }
            }
          })
    .when('/signup/:url_slug/password', {
            templateUrl: 'signup/signup.tpl.html',
            controller: 'signupCtrl',
            resolve:{
              userOwnsThisProfile: function(security){
                return security.testUserAuthenticationLevel("ownsThisProfile")
              }
            }
          })
    .when("/signup/*rest", {
      templateUrl: 'signup/signup.tpl.html',
      controller: 'signupCtrl',
      resolve:{
        userNotLoggedIn: function(security){
          return security.testUserAuthenticationLevel("loggedIn", false)
        }
      }
    })
    .when('/signup', {redirectTo: '/signup/name'})


}])

  .controller('signupCtrl', function($scope, Signup, Page, security){
    Page.setUservoiceTabLoc("bottom")
    Page.setTemplates("signup/signup-header", "")
//    security.logout()
    $scope.input = {}

    $scope.include =  Signup.getTemplatePath();
    $scope.nav = { // defined as an object so that controllers in child scopes can override...
      goToNextStep: function(){
        console.log("we should be overriding me.")
      }
    }


  })

  .controller( 'signupNameCtrl', function ( $scope, $location, Signup, Slug ) {
    $scope.nav.goToNextStep = function(){

      var slug = Slug.make($scope.input.givenName, $scope.input.surname)

      $location.path("signup/" + slug + "/url")
    }

  })

  .controller( 'signupUrlCtrl', function ( $scope, $http, Users, TipsService, Slug, $location, security) {
    var  nameRegex = /\/signup\/(.+?)\/url/
    var slug = nameRegex.exec($location.path())[1]

    $scope.input.url_slug = slug

    $scope.nav.goToNextStep = function(){
      var logMsg = "saving user for the first time"
      Users.save(
        {id: $scope.input.url_slug, idType: "url_slug", log:logMsg},
        {
          givenName: res[1],
          surname: res[2],
          url_slug: $scope.input.url_slug,
          tips: TipsService.keysStr()
        },
        function(resp, headers){
          console.log("got response back from save user", resp)
          security.clearCachedUser()
          $location.path("signup/" + $scope.input.url_slug + "/products/add")

        }
      )
    }
  })

  .controller( 'signupProductsCtrl', function($location, $scope, Signup, AllTheImporrity ) {
    var m = /\/signup\/(\w+)\//.exec($location.path())

    $scope.importers = AllTheImporters.get()
    $scope.nav.goToNextStep = function(){
      $location.path("signup/" + m[1] + "/password")
    }
  })

  .controller( 'signupPasswordCtrl', function ($scope, $location, security, UsersAbout, UsersPassword, Update) {
    var url_slug = /\/signup\/(\w+)\//.exec($location.path())[1]
    var redirectCb = function(){
      $location.path("/" + url_slug)
      security.requestCurrentUser()
    }

    $scope.nav.goToNextStep = function(){
      var emailLogMsg = "saving the email on signup"
      var pwLogMsg = "saving the password on signup"

      UsersAbout.patch(
        {"id": url_slug, idType:"url_slug", log: emailLogMsg},
        {about: {email: $scope.input.email}},
        function(resp) {
          console.log("we set the email", resp)
        }
      )

      UsersPassword.save(
        {"id": url_slug, idType:"url_slug"},
        {newPassword: $scope.input.password, log: pwLogMsg},
        function(data){
          console.log("we set the password; showing the 'updating' modal.")
          security.clearCachedUser()
          Update.showUpdate(url_slug, redirectCb)
        }
      )

    }
  })

.controller("signupHeaderCtrl", function($scope, Signup, Page) {

  Page.setTitle("signup")

  $scope.signupSteps = Signup.signupSteps();
  $scope.isStepCurrent = Signup.onSignupStep;
  $scope.isStepCompleted = Signup.isBeforeCurrentSignupStep;

})

;
