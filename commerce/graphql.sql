-- sample GraphQL query to test the endpoint

query SearchProducts {
  searchProducts(search: "soft") {
    id
    name
    price
    stock
  }
  item(id: 5) {
    name
  }
}


query GetProducts {
    hello
    products {
        id
        name
   }
}

-- mutation to insert new product
mutation {
   createProduct(
     name: "kwalba 23"
     description: "23 hau bottle"
     category: "Fashion"
     price: "53.88"
     stock: 6
   ) {
     product {
       id
       owner {
         id
       }
     }
   }
 }

query {
	hello
  item (id: 58) {
    name
  }
}
