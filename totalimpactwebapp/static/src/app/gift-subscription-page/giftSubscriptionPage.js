angular.module( 'giftSubscriptionPage', [
    'security',
    'services.page',
    'services.tiMixpanel'
  ])

  .config(function($routeProvider) {
    $routeProvider

    .when('/buy-subscriptions', {
      templateUrl: 'gift-subscription-page/gift-subscription-page.tpl.html',
      controller: 'giftSubscriptionPageCtrl'
    })
  })

  .controller("giftSubscriptionPageCtrl", function($scope,
                                         $http,
                                         $window,
                                         Page,
                                         TiMixpanel,
                                         Loading,
                                         UserMessage) {
    Page.setTitle("Buy subscriptions")
    $window.scrollTo(0, 0)

    var calculateCost = function(numSubscriptions){
      return numSubscriptions * 60
    }

    var donate = function(token){
      console.log("this is where the donate function works. sends this token: ", token)
      $http.post("/donate",
        {stripe_token: token},
        function(resp){}
      )
    }

    var clearForm = function(){
      $scope.formData = {}
      $scope.name = null
      $scope.number = null
      $scope.expiry = null
      $scope.cvc = null
    }


    var buyCoupons = function(stripeToken){
      console.log("buying teh coupons.")
      $http.post(
        "/coupons",
        {
          stripeToken: stripeToken,
          numSubscriptions: $scope.formData.numSubscriptions,
          cost: calculateCost($scope.formData.numSubscriptions),
          email: $scope.formData.email
        })
      .success(
        function(resp){
          console.log("we done bought us some coupons!", resp)
          UserMessage.setStr("Success! Check your email for your coupon code.", "success")
        })
      .error(
        function(resp){
          console.log("buyCoupons() fail")
          UserMessage.setStr("Sorry, something went wrong with your order!", "danger")
      })
      .finally(function(resp){
        window.scrollTo(0,0)
        clearForm()
          Loading.finish("subscribe")
      })
    }

    $scope.formData = {}
    $scope.cost = function(){
      return calculateCost($scope.formData.numSubscriptions)
    }





    $scope.handleStripe = function(status, response){
      Loading.start("subscribe")

      Loading.start("donate")
      console.log("in handleStripe(), got a response back from Stripe.js's call to the Stripe server:", status, response)
      if (response.error) {
        console.log("got an error instead of a token.")
        UserMessage.set("settings.subscription.subscribe.error")

      }
      else {
        console.log("yay, Stripe CC token created successfully! Now let's charge the card.")
        buyCoupons(response.id)
      }
    }

  })

