import random
import string

from odoo import models, fields, api
import logging
import json
import requests

from odoo.http import request

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ADDITIONAL FIELDS
    create_by = fields.Char(string="Créé à partir de ", default='Odoo')
    source = fields.Char('source')

    # SET THE HEADERS AND URLS OF ekiclik
    headers = {"Content-Type": "application/json",
               "Accept": "application/json", "Catch-Control": "no-cache"}
    url_client = "/api/odoo/client/clients"

    @api.model
    def create(self, vals):
        _logger.info(
        '\n\n\nvals\n\n\n\n--->>  %s\n\n\n\n', vals)
        # SET THE ENVIREMENT
        utils = self.env['odoo_utils']
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
            
        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)

        # CHECK IF THE CREATION MADE BY ekiclik---------------------------------------------------------------
        if 'create_by' in vals.keys() and vals['create_by'] != 'odoo':
            vals["create_by"] = 'ekiclik'
            _logger.info(
                '\n\n\ncreate by\n\n\n\n--->>  %s\n\n\n\n', vals['create_by'])
            try:
                # CHECK TYPE OF CLIENT IF PERSON
                if vals["is_company"] == False:
                    _logger.info(
                        '\n\n\n company\n\n\n\n--->>  %s\n\n\n\n', vals['is_company'])
                    if 'type' in vals and vals['type'] == 'delivery':

                        # PUT THE PARENT ID BY SEARCHING WITH SOURCE
                        if 'source' in vals and vals['source']:
                            # Get the bank record
                            bank = self.env['res.partner'].search([('name', '=', vals['source'])])
                            vals['parent_id'] = bank.id

                            vals.pop('source')

                        # PUT THE country_id [res.country] (Many2one Relation)
                        if 'country_id' in vals.keys():
                            country = self.env['res.country'].search([('code', '=', vals['country_id'])])

                            vals['country_id'] = country.id
                        # PUT THE state_id [res.country.state] (Many2one Relation)
                        if 'state_id' in vals.keys():
                            state_id = utils.affect_many_to_one(
                                vals['state_id'], 'res.country.state', 'name')
                            if state_id:
                                vals['state_id'] = state_id
                            else:
                                vals['state_id'] = None

                _logger.info(
                    '\n\n\ncreating partner\n\n\n\n--->>  %s\n\n\n\n', vals)
                response = super(ResPartner, self).create(vals)
                _logger.info(
                    '\n\n\npartner created \n\n\n\n--->>  %s\n\n\n\n', vals)


                #send back an update body to store the id_externe of the new client
                data_address = {
                    'name': response.name,
                    'email': response.email,
                    'phone': response.phone,
                    #'xml_id': self.get_external_id(),
                    'xml_id': response.id,
                }
                _logger.info(
                    '\n\n\n data \n\n\n\n--->>  %s\n\n\n\n', data_address)


                response1 = requests.put(str(domain) + self.url_client, data=json.dumps(data_address),
                                         headers=self.headers)


                _logger.info(
                    '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response1)
                response2 = requests.put(str(domain_cpa) + self.url_client, data=json.dumps(data_address),
                                         headers=self.headers)


                _logger.info(
                    '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response2)
                return response

            except Exception as e:
                _logger.error("An error occurred: %s", e)
                raise
        else:
            # For other cases, delegate to the parent class
            return super(ResPartner, self).create(vals)

    def write(self, vals):

        # SET THE ENVIREMENT
        utils = self.env['odoo_utils']
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa


        # THIS CONDITION IS MADE BECAUSE OF
        # PATH IN THE CONTAINER usr/lib/python3/dist-packags/odoo/addons/base/models/res_partner.py line 600 (you can check it)
        # PATH IN THE CONTAINER usr/lib/python3/dist-packags/odoo/addons/base/models/res_partner.py line 142 (you can check it)
        if (len(vals.keys()) == 1 and ('is_company' in vals.keys()) or ('lang' in vals.keys()) or (
                'debit_limit' in vals.keys())) or len(vals.keys()) == 2 and (
                'vat' in vals.keys() and 'credit_limit' in vals.keys()) or (
                (('commercial_partner_id' in vals.keys()) or ('num_client' in vals.keys())) and (
                len(vals.keys()) == 1)):
            _logger.info(
                '\n\n\ncreate called write\n\n\n\n--->>  %s\n\n\n\n', vals)
            return super(ResPartner, self).write(vals)

        # CHECK IF UPDATE MADE BY ekiclik--------------------------------------------------------------------------------------
        if 'create_by' in vals.keys():
            # PUT THE country_id [res.country] (Many2one Relation)
            if 'country_id' in vals.keys():
                country_id = utils.affect_many_to_one(
                    vals['country_id'], 'res.country', 'code')
                if country_id:
                    vals['country_id'] = country_id
                else:
                    vals['country_id'] = None

            # PUT THE state_id [res.country.state] (Many2one Relation)
            if 'state_id' in vals.keys():
                state_id = utils.affect_many_to_one(
                    vals['state_id'], 'res.country.state', 'name')
                if state_id:
                    vals['state_id'] = state_id
                else:
                    country_id = self.env['res.country'].search([('code', '=', 'DZ')])
                    _logger.info('\n\n\n(from update) state creation\n\n\n\n--->>  %s\n\n\n\n', vals['state_id'][0:3])
                    if country_id:
                        # Create the state
                        created_state = self.env['res.country.state'].create({
                            'name': vals['state_id'],
                            'code': vals['state_id'][0:3],
                            'country_id': country_id.id,
                        })
                        vals['state_id'] = created_state.id
                        _logger.info('\n\n\n(from update) state creation\n\n\n\n--->>  %s\n\n\n\n', created_state.name)

            # PUT THE PARENT ID BY SEARCHING WITH SOURCE
            if 'source' in vals and vals['source']:
                # Get the bank record
                bank = self.env['res.partner'].search([('name', '=', vals['source'])])
                vals['parent_id'] = bank.id

                vals.pop('source')

            response = super(ResPartner, self).write(vals)
            _logger.info(
                '\n\n\nresponse value is :  \n\n\n\n\n--->  %s\n\n\n\n\n\n\n', response)

            if response:
                _logger.info(
                    '\n\n\nclient updated from ekiclik \n\n\n\n\n--->  %s\n\n\n\n\n\n\n', vals)
            return response

        # UPDATE MADE BY ODOO--------------------------------------------------------------------------------------------------
        else:
            res = super(ResPartner, self).write(vals)
            if res:
                data_address = {
                    'name': self.name,
                    'email': self.email,
                    #'xml_id': self.get_external_id(),
                    'xml_id': self.id,
                    'country_id': self.country_id.name,
                    'state_id': self.state_id.name,
                    'phone': self.phone,
                }
                _logger.info(
                    '\n\n\n data to send \n\n\n\n--->>  %s\n\n\n\n', data_address)
                response1 = requests.put(str(domain) + self.url_client, data=json.dumps(data_address),
                                         headers=self.headers)
                _logger.info(
                    '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response1)
                response2 = requests.put(str(domain_cpa) + self.url_client, data=json.dumps(data_address),
                                         headers=self.headers)
                _logger.info(
                    '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response2)

            return res
