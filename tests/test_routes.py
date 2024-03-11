######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product, DataValidationError
from tests.factories import ProductFactory
from unittest.mock import patch

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    def test_deserialize(self):
        """Deserialize"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------

    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """Read a product"""
        test_product = self._create_products(1)[0]
        API_repsonse = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(API_repsonse.status_code, status.HTTP_200_OK)
        data = API_repsonse.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """Get a product that cannot be find"""
        API_repsonse = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(API_repsonse.status_code, status.HTTP_404_NOT_FOUND)
        data = API_repsonse.get_json()
        self.assertIn("was not found", data["message"])

    def test_update_product(self):
        """Update a product"""
        test_product = ProductFactory()
        API_repsonse = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(API_repsonse.status_code, status.HTTP_201_CREATED)
        new_product = API_repsonse.get_json()
        new_product["description"] = "unknown"
        API_repsonse = self.client.put(f"{BASE_URL}/{new_product['id']}", json=new_product)
        self.assertEqual(API_repsonse.status_code, status.HTTP_200_OK)
        updated_product = API_repsonse.get_json()
        self.assertEqual(updated_product["description"], "unknown")

    def test_delete_product(self):
        """Delete a product"""
        products = self._create_products(5)
        product_count = self.get_product_count()
        test_product = products[0]
        API_repsonse = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(API_repsonse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(API_repsonse.data), 0)
        API_repsonse = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(API_repsonse.status_code, status.HTTP_404_NOT_FOUND)
        new_count = self.get_product_count()
        self.assertEqual(new_count, product_count - 1)

    def test_get_product_list(self):
        """Get a list of all products"""
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_query_by_name(self):
        """Search products by name"""
        products = self._create_products(5)
        test_name = products[0].name
        name_count = len([product for product in products if product.name == test_name])
        response = self.client.get(BASE_URL, query_string=f"name={quote_plus(test_name)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), name_count)
        for product in data:
            self.assertEqual(product["name"], test_name)

    def test_query_by_category(self):
        """Search products by category"""
        products = self._create_products(10)
        category = products[0].category
        found = [product for product in products if product.category == category]
        found_count = len(found)
        logging.debug("Found Products [%d] %s", found_count, found)
        response = self.client.get(BASE_URL, query_string=f"category={category.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), found_count)
        for product in data:
            self.assertEqual(product["category"], category.name)

    def test_query_by_availability(self):
        """Search products by availability"""
        products = self._create_products(10)
        available_products = [product for product in products if product.available is True]
        available_count = len(available_products)
        response = self.client.get(BASE_URL, query_string="available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), available_count)
        for product in data:
            self.assertEqual(product["available"], True)

    def test_invalid_name(self):
        """Invalid name"""
        product = Product()
        invalid_data = {
            "description": "Test Description",
            "price": "10.00",
            "available": True,
            "category": "SOME_CATEGORY"
        }
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(invalid_data)
        self.assertIn("name", str(context.exception))

    def test_invalid_description(self):
        product = Product()
        invalid_data = {
            "name": "Test Product",
            "price": "10.00",
            "available": True,
            "category": "SOME_CATEGORY"
        }
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(invalid_data)
        self.assertIn("description", str(context.exception))

    def test_invalid_price(self):
        product = Product()
        invalid_data = {
            "name": "Test Product",
            "description": "Test Description",
            "available": True,
            "category": "SOME_CATEGORY"
        }
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(invalid_data)
        self.assertIn("price", str(context.exception))

    def test_invalid_available(self):
        product = Product()
        invalid_data = {
            "name": "Test Product",
            "description": "Test Description",
            "price": "10.00",
            "available": "not_bool",
            "category": "SOME_CATEGORY"
        }
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(invalid_data)
        self.assertIn("available", str(context.exception))

    @patch('service.models.Product.find')
    def test_update_product_not_found(self, mock_find):
        # Mock the Product.find method to return None
        mock_find.return_value = None

        # Send a PUT request to update a non-existent product
        with app.test_client() as client:
            response = client.put('/products/123', json={
                "name": "Updated Product",
                "description": "Updated Description",
                "price": "10.00",
                "available": True,
                "category":
                "SOME_CATEGORY"})

            # Check that the response has status code 404
            self.assertEqual(response.status_code, 404)

            # Check that the response contains the expected error message
            expected_error_message = "Product with id '123' was not found."
            self.assertIn(expected_error_message, response.json['message'])

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        logging.debug("data = %s", data)
        return len(data)
