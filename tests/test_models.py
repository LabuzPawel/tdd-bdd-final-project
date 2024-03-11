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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_a_product(self):
        """Read a product"""
        product = ProductFactory()
        product.create()
        self.assertNotEqual(product.id, None)
        find_product = Product.find(product.id)
        self.assertEqual(product.id, find_product.id)
        self.assertEqual(product.name, find_product.name)
        self.assertEqual(product.description, find_product.description)
        self.assertEqual(product.price, find_product.price)
        self.assertEqual(product.available, find_product.available)
        self.assertEqual(product.category, find_product.category)

    def test_update_a_product(self):
        """Update a product"""
        product = ProductFactory()
        product.create()
        self.assertNotEqual(product.id, None)

        product_id = product.id
        new_name = 'Test_name'
        new_description = 'Test_discription'

        product.name = new_name
        product.description = new_description
        product.update()

        self.assertEqual(product.id, product_id)
        self.assertEqual(product.name, new_name)
        self.assertEqual(product.description, new_description)

        all_products = Product.all()
        self.assertEqual(len(all_products), 1)
        self.assertEqual(all_products[0].id, product_id)
        self.assertEqual(all_products[0].name, new_name)
        self.assertEqual(all_products[0].description, new_description)

    def test_delete_a_product(self):
        """"Delete a product"""
        product = ProductFactory()
        product.create()
        self.assertNotEqual(product.id, None)
        product.delete()
        all_products = Product.all()
        self.assertEqual(len(all_products), 0)

    def test_list_all_products(self):
        """List all products"""
        self.assertEqual(len(Product.all()), 0)
        for product_ in range(10):
            product = ProductFactory()
            product.create()
        self.assertEqual(len(Product.all()), 10)

    def test_find_by_name(self):
        """Find product by name"""
        name_list = []
        for product_ in range(10):
            product = ProductFactory()
            product.create()
            name_list.append(product.name)
        self.assertEqual(len(Product.all()), 10)
        all_products = Product.all()
        name = all_products[0].name
        count = 0
        for number in range(len(all_products)):
            if all_products[number].name == name:
                count += 1
        found_by_name_products = Product.find_by_name(name).count()
        self.assertEqual(count, found_by_name_products)

    def test_find_by_availability(self):
        """Find a product by availability"""
        for product_ in range(10):
            product = ProductFactory()
            product.create()
        self.assertEqual(len(Product.all()), 10)
        all_products = Product.all()
        available = True
        count = 0
        for number in range(10):
            if all_products[number].available == available:
                count += 1
        self.assertEqual(Product.find_by_availability().count(), count)

    def test_find_by_category(self):
        """Find a product by category"""
        for product_ in range(10):
            product = ProductFactory()
            product.create()
        self.assertEqual(len(Product.all()), 10)
        all_products = Product.all()
        category = all_products[0].category
        count = 0
        for x in range(len(all_products)):
            if all_products[x].category == category:
                count += 1
        found_by_category_products = Product.find_by_category(category).count()
        self.assertEqual(count, found_by_category_products)

    def test_update_without_id(self):
        """Update a product without id"""
        product = ProductFactory()
        product.create()
        product.id = None
        self.assertRaises(DataValidationError, product.update)
