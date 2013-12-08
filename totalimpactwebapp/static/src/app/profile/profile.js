angular.module("profile", [
  'resources.users',
  'product.product',
  'services.page',
  'ui.bootstrap',
  'security',
  'profile.addProducts',
  'product.categoryHeading'
])

.config(['$routeProvider', function ($routeProvider) {

  $routeProvider.when("/embed/:url_slug", {
    templateUrl:'profile/profile.tpl.html',
    controller:'ProfileCtrl'
  })

}])

.factory('UserProfile', function($window, $anchorScroll, $location, UsersAbout, security, Slug, Page){
  var about = {}


  return {

    getGenreIcon: function(){

    },


    filterProducts: function(products, filterBy) {
      var productsWithMetrics = _.filter(products, function(x){return _.size(x.metrics); });
      var productsWitoutMetrics = _.filter(products, function(x){return x.metrics && _.size(x.metrics)==0; });

      if (filterBy == "withMetrics") {
        return productsWithMetrics;
      }
      else if (filterBy === "withoutMetrics") {
        return productsWitoutMetrics;
      }
      else {
        return productsWithMetrics.concat(productsWitoutMetrics);
      }
    },
    scrollToCorrectLocation: function(){
      if ($location.hash()){
        $anchorScroll()
      }
      else {
        var lastScrollPos = Page.getLastScrollPosition($location.path())
        $window.scrollTo(0, lastScrollPos)
      }
    },
    loadUser: function($scope, slug) {
      return UsersAbout.get(
        {
          id: slug,
          idType: "url_slug"
        },
        function(resp) { // success
          Page.setTitle(resp.about.given_name + " " + resp.about.surname)
        },
        function(resp) { // fail
          if (resp.status == 404) {
            $scope.userExists = false;
            $scope.slug = slug;
          }
        }
      );
    },
    slugIsCurrentUser: function(slug){
      if (!security.getCurrentUser()) return false;
      return (security.getCurrentUser().url_slug == slug);
    },
    makeSlug: function(){
      about.url_slug = Slug.make(about.givenName, about.surname)
    },
    readyToCreateOnServer: function(){
      return about.url_slug && !id;
    },

    reset:function(){
      about = {}
    },

    setId: function(newId){id = newId},
    getId: function(){return id},
    getSlug: function(){return about.url_slug},
    "about": about
  }
})

.controller('ProfileCtrl', function (
    $scope,
    $rootScope,
    $location,
    $routeParams,
    $modal,
    $timeout,
    $http,
    $anchorScroll,
    $window,
    UsersProducts,
    Product,
    UserProfile,
    CategoryHeading,
    Page) {
    if (Page.isEmbedded()){
      // do embedded stuff. i don't think we're using this any more?
    }

    $scope.$on('ngRepeatFinished', function(ngRepeatFinishedEvent) {
      // fired by the 'on-repeat-finished" directive in the main products-rendering loop.

      // twttr is a GLOBAL VAR loaded by the twitter widget script called in
      //    bottom.js. it will break in unit tests, so fix before then.
      twttr.widgets.load()

      console.log("load!")

    });


    var userSlug = $routeParams.url_slug;
    var loadingProducts = true
    $scope.loadingProducts = function(){
      return loadingProducts
    }
    $scope.userExists = true;
    $scope.showProductsWithoutMetrics = false;
    $scope.filterProducts =  UserProfile.filterProducts;

    $scope.user = UserProfile.loadUser($scope, userSlug);
    $scope.currentUserIsProfileOwner = function(){
      return UserProfile.slugIsCurrentUser(userSlug);
    }

    $scope.openProfileEmbedModal = function(){
      $modal.open({
        templateUrl: "profile/profile-embed-modal.tpl.html",
        controller: "profileEmbedModalCtrl",
        resolve: {
          userSlug: function($q){ // pass the userSlug to modal controller.
            return $q.when(userSlug)
          }
        }
      })
    }


    $scope.getSortScore = function(product) {
      return Product.getSortScore(product) * -1;
    }

    var renderProducts = function(){
      $scope.products = UsersProducts.query({
        id: userSlug,
        includeHeadingProducts: true,
        idType: "url_slug"
      },
        function(resp){
          loadingProducts = false
          // scroll to any hash-specified anchors on page. in a timeout because
          // must happen after page is totally rendered.
          $timeout(function(){
            UserProfile.scrollToCorrectLocation()
          }, 0)

        },
        function(resp){loadingProducts = false}
      );
    }
    $timeout(renderProducts, 100)
})


.controller("CategoryHeadingCtrl", function($scope, CategoryHeading){
    $scope.genreIcon = CategoryHeading.getGenreIcon

})






.controller("profileEmbedModalCtrl", function($scope, Page, userSlug){
  console.log("user slug is: ", userSlug)
  $scope.userSlug = userSlug;
  $scope.baseUrl = Page.getBaseUrl()
})





.directive("backToProfile",function($location){
 return {
   restrict: 'A',
   replace: true,
   template:"<a ng-show='returnLink' class='back-to-profile' href='/{{ returnLink }}'><i class='icon-chevron-left'></i>back to profile</a>",
   link: function($scope,el){
     var re = /^\/(\w+)\/product\/(\w+)/
     var m = re.exec($location.path())
     $scope.returnLink = null

     if (m) {
       var url_slug = m[1]

       if (url_slug != "embed") {
         $scope.returnLink = url_slug
       }
     }
   }
 }
})




