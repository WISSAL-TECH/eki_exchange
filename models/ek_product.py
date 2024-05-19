import json
import sys

import boto3
import requests
# from minio import Minio
import re
from odoo import models, fields, api, exceptions, _
from odoo.http import request
import logging
from _datetime import datetime
from odoo.exceptions import ValidationError

from urllib.parse import quote
from io import BytesIO, StringIO
from .config import *
import base64
import random
import string

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = ['product.template']

    create_by = fields.Char(string="Créé à partir de", readonly=True)
    brand = fields.Many2one("product.brand", 'Marque')
    image_url = fields.Char(string='Image URL')
    manufacture_name = fields.Char(string='Fabricant')
    certificate = fields.Binary("Certificat")
    certificate_url = fields.Char("Certificate URL", compute='_compute_certificate_url')
    ref_odoo = fields.Char("ref odoo")
    constructor_ref = fields.Char("Réference constructeur",
                                  #default="Merci de Générer/entrer une référence constructeur",
                                  required=True)
    brand_id = fields.Many2one("product.brand", string="Marque", required=True)
    default_code = fields.Char(string="Reference interne", invisible=True)
    company_id = fields.Many2one("res.company", string="Société", invisible=True)
    categ_id = fields.Many2one("product.category", string="Catégorie d'article", required=True)
    attribute_line_ids = fields.One2many('product.template.attribute.line', 'product_tmpl_id', 'Product Attributes',
                                         copy=True, required=True)
    detailed_type = fields.Selection([
        ('consu', 'Consommable'),
        ('service', 'Service'), ('product', 'Article stockable')], string="Type d'article", default='product',
        required=True,
        help=
        "Un produit stockable est un produit dont on gère le stock. L'application \"Inventaire\" doit être installée. \n"
        "Un produit consommable, d'un autre côté, est un produit pour lequel le stock n'est pas géré.\n"
        "Un service est un produit immatériel que vous fournissez.")

    prix_central = fields.Float("Prix centrale des achats", compute='_compute_prix_central')
    prix_ek = fields.Float("Prix ekiclik", compute='_compute_prix_ek')
    @api.depends('standard_price', 'taxes_id')
    def _compute_prix_central(self):
        """ Compute the value of prix_central """
        for record in self:
            price = 0
            if record.taxes_id:
                taxe = 0
                for tax in record.taxes_id:
                    taxe += (record.standard_price * tax.amount) / 100
                price = record.standard_price + taxe

            marge1 = (record.standard_price * 11.1) / 100
            record.prix_central = price + marge1

    @api.depends('standard_price', 'taxes_id')
    def _compute_prix_ek(self):
        """ Compute the value of prix_ek """
        for record in self:
            price = 0
            if record.taxes_id:
                taxe = 0
                for tax in record.taxes_id:
                    taxe += (record.standard_price * tax.amount) / 100
                price = record.standard_price + taxe

            marge2 = (record.standard_price * 61) / 100
            record.prix_ek = price + marge2


    def generate_unique_reference(self):
        # Generate 5 random letters
        letters = ''.join(random.choices(string.ascii_uppercase, k=5))

        # Generate 5 random numbers
        numbers = ''.join(random.choices(string.digits, k=5))

        # Combine letters and numbers to create the reference
        new_reference = letters + numbers

        return new_reference

    def action_generate_reference(self):
        for record in self:
            new_reference = record.generate_unique_reference()
            record.constructor_ref = new_reference

    @api.constrains('attribute_line_ids')
    def _check_attribute_line_ids(self):
        for record in self:
            if not record.attribute_line_ids:
                raise ValidationError(
                    _("Dans l'onglet Attributs et variantes veuillez sélectionner au moins une variante."))

    @api.depends('certificate')
    def _compute_certificate_url(self):
        for record in self:
            record.certificate_url = ''

    # set the url and headers
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        logging.warning("create product ======")
        logging.warning(vals)
        random_number = random.randint(100000, 999999)

        vals["ref_odoo"] = "rc_" + str(random_number)
        
        rec = super(Product, self).create(vals)

        # 1- CREATE A PRODUCT FROM ekiclik
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
        url_product = "/api/odoo/products"

        if 'create_by' in vals.keys() and vals['create_by'] != 'Odoo':
            if 'barcode' in vals and not vals['barcode']:
                vals.pop('barcode')

            vals['create_by'] = "Ekiclik"
            if "brand" in vals and vals["brand"]:
                brand = self.env['product.brand'].search([('name', '=', vals['brand'])])
                if brand:
                    vals['brand_id'] = brand.id
                else:
                    brand = self.env['product.brand'].create({
                        'name': vals['brand']
                    })
                    vals['brand_id'] = brand.id
            vals.pop('brand')
            if "list_price" in vals and not vals["list_price"]:
                vals.pop('list_price')

            if 'category' in vals and vals['category']:
                # Get the category record
                category = self.env['product.category'].search([('name', '=', vals['category'])])
                if category:
                    vals['categ_id'] = category.id
                else:
                    category = self.env['product.category'].create({
                        'name': vals['category']
                    })
                    vals['categ_id'] = category.id
            elif 'category' in vals and vals['category'] is None:
                vals.pop('category')
            # GET IMAGE URL AND AUTOMATICALLY DISPLAY IT ON ODOO
            if "image_url" in vals and vals["image_url"]:
                image = base64.b64encode(requests.get(vals["image_url"]).content)
                vals["image_1920"] = image
                vals.pop("image_url")

            rec = super(Product, self).create(vals)

        return rec

        # 2- CREATE A PRODUCT FROM ODOO (Send a product to ekiclik)


    # def create_doc_url(self, attach):
    # client = Minio("play.min.io",
    #               access_key="admin",
    #               secret_key="d%gHsjnZ*eD")
    # bucket_name = "file-storage-document-salam"
    # destination_file = "eki_file"+str(attach.id)

    # if attach.datas:
    #    data_fileobj = BytesIO(base64.standard_b64decode(attach.datas))

    #    client.fput_object(
    #       bucket_name, destination_file, data_fileobj,
    #    )

    # Get the URL for the uploaded file
    #    url = client.presigned_get_object(bucket_name, destination_file)

    #    print(
    #        data_fileobj, "successfully uploaded as object",
    #        destination_file, "to bucket", bucket_name,
    #    )

    #    attach.write({'url': url})

    def write(self, vals):

        _logger.info(
            '\n\n\n update\n\n\n\n--->>  %s\n\n\n\n', vals)

        rec = super(Product, self).write(vals)

        return rec



class EkiProduct(models.Model):
    _inherit = ['product.product']

    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}
    manufacture_name = fields.Char(string='Fabricant')
    reference = fields.Char(string='Réference')
    ref_odoo = fields.Char("ref odoo")
    barcode = fields.Char("Code-barres", readonly=True)
    certificate = fields.Binary("Certificat")
    certificate_url = fields.Char("Certificate URL")
    image_url = fields.Char()
    image_count = fields.Float()
    name_store = fields.Char("name")
    prix_central = fields.Float("Prix centrale des achats")
    prix_ek = fields.Float("Prix ekiclik")
    @api.depends('standard_price', 'taxes_id')
    def _compute_prix_central(self):
        """ Compute the value of prix_central """
        for record in self:
            price = 0
            if record.taxes_id:
                taxe = 0
                for tax in record.taxes_id:
                    taxe += (record.standard_price * tax.amount) / 100
                price = record.standard_price + taxe

            marge1 = (record.standard_price * 11.1) / 100
            record.prix_central = price + marge1

    @api.depends('standard_price', 'taxes_id')
    def _compute_prix_ek(self):
        """ Compute the value of prix_ek """
        for record in self:
            price = 0
            if record.taxes_id:
                taxe = 0
                for tax in record.taxes_id:
                    taxe += (record.standard_price * tax.amount) / 100
                price = record.standard_price + taxe

            marge2 = (record.standard_price * 50) / 100
            record.prix_ek = price + marge2
    @api.onchange('standard_price')
    def _onchange_cout(self):
        """ Compute the value of prix_ek prix_centrale  """
        _logger.info('\n\n\n onchange cout PRODUCT \n\n\n\n--->> \n\n\n\n')
        for record in self:
            price = 0
            if record.taxes_id:
                taxe = 0
                for tax in record.taxes_id:
                    taxe += (record.standard_price * tax.amount) / 100
                price = record.standard_price + taxe

            marge2 = (record.standard_price * 61) / 100
            record.prix_ek = round(price + marge2, 2)
            marge1 = (record.standard_price * 11.1) / 100
            record.prix_central = round(price + marge1,2)

    def create_doc_url(self, attach):
        s3 = boto3.client('s3',
                          aws_access_key_id='AKIAXOFYUBQFSP2WOT5R',
                          aws_secret_access_key='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',
                          region_name='eu-west-2'
                          )
        bucket = "wicommerce-storage"
        if attach.datas:
            # Generate a unique S3 key for the image
            s3_key = f'attachments/{attach.res_id}{attach.name}'
            s3_key_encoded = quote(s3_key)
            # Convert the image binary data to a BytesIO object
            data_fileobj = BytesIO(base64.standard_b64decode(attach.datas))

            # Upload the image to S3
            s3.put_object(Bucket=bucket, Key=s3_key, Body=data_fileobj, ContentType=attach.mimetype)

            # Construct the S3 image URL
            s3_url = f'https://{bucket}.s3.eu-west-2.amazonaws.com/{s3_key_encoded}'

            # Update the product record with the S3 image URL
            return s3_url

    def generate_code(self):
        """Generating default code for ek products"""

        # Generate a random 6-digit number
        random_number = random.randint(100000, 999999)

        # Concatenate the "eki_" and random number
        product_code = f"eki_{random_number}"

        return product_code

    def generate_name_variante(self, name, ref, variante):
        """Generating name for ek products"""
        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)
        # Add default code if exists

        if ref:
            name += ' ' + ref
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)
        if variante:
            for v in variante:
                name += ' ' + str(v)
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        return name

    def generate_name(self, vals):
        """Generating name for ek products"""
        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n')
        # _logger.info('\n\n\n vals NAME\n\n\n\n--->  %s\n\n\n\n',vals["name"])
        # _logger.info('\n\n\n self NAME\n\n\n\n--->  %s\n\n\n\n',self.name)
        name = ''
        if "name" in vals and vals['name'] or self.name:
            name = vals['name'] if "name" in vals and vals['name'] else self.name

        # Iterate through each record in the Many2Many field
        for variant_value in self.product_template_variant_value_ids:
            name += ' ' + str(variant_value.name)
            _logger.info('\n\n\n  NAME with variantes\n\n\n\n--->  %s\n\n\n\n', name)

        # Add brand name if exists
        # name += ' ' + str(self.brand_id.name) if self.brand_id else ''

        # Add default code if exists
        if "reference" in vals and vals["reference"]:
            name += ' ' + vals["reference"]
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        elif self.reference:
            name += ' ' + str(self.reference)
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        return name
    def _generate_reference(self):
        # Generate a default reference
        return 'ref_' + str(random.randint(100000, 999999))
    @api.model
    def create(self, vals):
        # Appeler la méthode de création de la classe parente
        random_number = random.randint(100000, 999999)
        vals["ref_odoo"] = "rc_variante" + str(random_number)
        if 'reference' not in vals or not vals['reference']:
            vals['reference'] = self._generate_reference()

        _logger.info('\n\n\n creating variante vals\n\n\n\n--->  %s\n\n\n\n', vals)
        rec = super(EkiProduct, self).create(vals)
        return rec

    def write(self, vals):
        result = super(EkiProduct, self).write(vals)
        _logger.info('Write operation successful with vals: %s', vals)
        return result
