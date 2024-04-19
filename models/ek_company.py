from odoo import models, fields, api
import logging
import json
import sys

import requests
# from minio import Minio
import re
from odoo import models, fields, api, exceptions
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EkWilaya(models.Model):
    _name = 'ek.wilaya'
    _rec_name = 'name'

    name = fields.Char("Wilaya")
class EkCommune(models.Model):
    _name = 'ek.commune'
    _rec_name = 'name'

    name = fields.Char("Commune")

class ResCompany(models.Model):
    _inherit = 'res.company'

    create_by = fields.Char()
    source = fields.Char()
    pos_commune = fields.Many2one("ek.commune", "Commune")
    pos_wilaya = fields.Many2one("ek.wilaya", "Wilaya")
    country_id = fields.Many2one('res.country', string='Country', required=True, default=lambda self: self._default_country())

    @api.model
    def _default_country(self):
        algeria = self.env['res.country'].search([('name', '=', 'Algérie')], limit=1)
        return algeria.id if algeria else False

    def _check_codification_length(self, vals):
        codification = vals.get('codification')
        if codification and len(codification) != 21:
            raise UserError("Codification must be 21 characters long.")

    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    def write(self, vals):
        self._check_codification_length(vals)
        logging.warning("create pos ======")
        logging.warning(vals)
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
        url_pos = "/api/odoo/pos"
        logging.warning("update pos from odoo ======")
        logging.warning(vals)

        # Check if 'pos' is in vals and if its value is True
        if vals.get('pos') or any(self.filtered(lambda r: r.pos)):
            # Prepare data for requests
            body = {}
            no_mobile = self.mobile if self.mobile else ''
            wilaya = self.env['res.country.state'].browse(vals['state_id']).name if 'state_id' in vals else self.state_id.name
            commune = self.env['ek.commune'].browse(vals['pos_commune']).name if 'pos_commune' in vals else self.pos_commune.name
            name_pos = vals.get('name') if 'name' in vals else self.name
            address_pos = vals.get('street') if 'street' in vals else self.street
            pos_phone_one = vals.get('phone') if 'phone' in vals else self.phone
            pos_phone_two = vals.get('mobile') if 'mobile' in vals else no_mobile
            codification = vals.get('codification', self.codification) if 'codification' in vals else self.codification
            source = vals.get('source') if 'source' in vals else self.source

            body["name_pos"] = name_pos
            body["address_pos"] = address_pos
            body["pos_phone_one"] = pos_phone_one
            body["pos_phone_two"] = pos_phone_two
            body["pos_wilaya"] = wilaya
            body["pos_commune"] = commune
            body["codification"] = codification
            body["status"] = "ACTIVE"
            body["source"] = source

            logging.warning("updated body ======")
            logging.warning(body)

            ek_user_emails = []
            user =  {}

            if "users" in vals:
                users = self.env['res.users'].browse(vals['users'])
                if users:
                    user["username"] = users.name
                    user["firstname"] = users.first_name
                    user["lastname"] = users.last_name
                    user["phone"] = users.phone
                    user["address"] = users.address
                    user["codification"] = users.codification
                    user["role"] = users.roles
                    user["email"] = users.login


            elif self.users:
                user["username"] = self.users.name
                user["firstname"] = self.users.first_name
                user["lastname"] = self.users.last_name
                user["phone"] = self.users.phone
                user["address"] = self.users.address
                user["codification"] = self.users.codification
                user["role"] = self.users.roles
                user["email"] = self.users.login

            logging.warning("create pos (user values) ======")
            logging.warning(user)
            ek_user_emails.append(user)

            pos_users_list = {}

            if "pos_user" in vals:
                pos_id = vals['pos_user']  # Get the ID of the 'pos' field from vals

                pos_record = self.env['res.users'].browse(pos_id)
                if pos_record:
                    pos_users_list["username"] = pos_record.name
                    pos_users_list["firstname"] = pos_record.first_name
                    pos_users_list["lastname"] = pos_record.last_name
                    pos_users_list["phone"] = pos_record.phone
                    pos_users_list["address"] = pos_record.address
                    pos_users_list["codification"] = pos_record.codification
                    pos_users_list["role"] = pos_record.roles
                    pos_users_list["email"] = pos_record.login


            elif self.pos_user:
                pos_users_list["username"] = self.pos_user.name
                pos_users_list["firstname"] = self.pos_user.first_name
                pos_users_list["lastname"] = self.pos_user.last_name
                pos_users_list["phone"] = self.pos_user.phone
                pos_users_list["address"] = self.pos_user.address
                pos_users_list["codification"] = self.pos_user.codification
                pos_users_list["role"] = self.pos_user.roles
                pos_users_list["email"] = self.pos_user.login

            logging.warning("create pos (pos user values) ======")
            logging.warning(pos_users_list)
            ek_user_emails.append(pos_users_list)

            body["users"] = ek_user_emails

            # Make requests to external services
            logging.warning("update pos ======")
            logging.warning(body)
            response_cpa = requests.put(str(domain_cpa) + str(url_pos), data=json.dumps(body), headers=self.headers)
            _logger.info('(UPDATE POS) response from cpa: %s', response_cpa.content)

            response = requests.put(str(domain) + str(url_pos), data=json.dumps(body), headers=self.headers)
            _logger.info('(UPDATE POS) response from alsalam: %s', response.content)

        # Perform database write operation
        rec = super(ResCompany, self).write(vals)

        return rec

    @api.model
    def create(self, vals):
        self._check_codification_length(vals)

        logging.warning("create pos ======")
        logging.warning(vals)
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
        url_pos = "/api/odoo/pos"

        if 'create_by' in vals and vals.get('create_by') != 'odoo':
            logging.warning("create pos from ekiclik ======")
            logging.warning(vals)


            body = {"params": {
                "data": {
                }
            }
            }
            data = {"name_pos": vals.get('name_pos'),
                    "address_pos": vals.get('address_pos'),
                    "pos_phone_one": vals.get('pos_phone_one'),
                    "pos_phone_two": vals.get('pos_phone_two'),
                    "pos_wilaya": vals.get('pos_wilaya'),
                    "pos_commune": vals.get('pos_commune'),
                    "codification": vals.get('codification'),
                    "status": vals.get('status'),
                    "source": vals.get('source')}
            ek_user_emails = []

            if "ek_user_emails" in vals and vals['ek_user_emails']:
                for value in vals['ek_user_emails']:
                    ek_user_emails.append(value)

            data["ek_user_emails"] = ek_user_emails
            body["data"] = data
            _logger.info(
                '\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', body)
            if "source" in vals and vals.get('source'):
                if vals['source'] == 'salam':
                    # envoyer pdv a cpa
                    _logger.info(
                        '\n\n\n pos BODY JSON \n\n\n\n--->>  %s\n\n\n\n', body)
                    response_cpa = requests.post(str(domain_cpa) + str(url_pos), data=json.dumps(body),
                                                 headers=self.headers)
                    _logger.info('\n\n\n(CREATE pos) response from cpa\n\n\n\n--->  %s\n\n\n\n',
                                 response_cpa.content)
                elif vals['source'] == "cpa":
                    _logger.info(
                        '\n\n\n pos BODY JSON \n\n\n\n--->>  %s\n\n\n\n', body)
                    response = requests.post(str(domain) + str(url_pos), data=json.dumps(body),
                                             headers=self.headers)
                    _logger.info('\n\n\n(CREATE pos) response from alsalam \n\n\n\n--->  %s\n\n\n\n',
                                 response.content)
            vals.pop("ek_user_emails")
            vals.pop("source")
            vals.pop("pos_commune")
            vals.pop("pos_wilaya")
            vals.pop("status")
            vals["name"] = vals.get('name_pos')
            vals.pop("name_pos")
            logging.warning("create pos from ek ======")
            logging.warning(vals)
            rec = super(ResCompany, self).create(vals)

            return rec
        else:
            logging.warning("create pos from odoo ======")
            logging.warning(vals)
            rec = super(ResCompany, self).create(vals)

            if 'pos' in vals and vals['pos'] == True:
                body = {}

                wilaya = ""
                if 'state_id' in vals and vals['state_id']:
                    state = self.env['res.country.state'].search([('id', '=', vals['state_id'])], limit=1)
                    wilaya = state.name
                commune = ""
                if 'pos_commune' in vals and vals['pos_commune']:
                    state = self.env['ek.commune'].search([('id', '=', vals['pos_commune'])], limit=1)
                    commune = state.name
                data = {"name_pos": vals.get('name') if vals.get('name') else '',
                        "address_pos": vals.get('street') if vals.get('street') else '',
                        "pos_phone_one": vals.get('phone') if vals.get('phone') else '',
                        "pos_phone_two": vals.get('mobile') if vals.get('mobile') else '',
                        "pos_wilaya": wilaya if wilaya else self.state_id.name,
                        "pos_commune": commune if commune else self.pos_commune.name,
                        "codification": vals.get('codification') if vals.get('codification') else '',
                        "status": "ACTIVE",
                        "source": vals.get('source') if vals.get('source') else ''}
                ek_user_emails = []
                user = {}

                if "users" in vals:
                    users = self.env['res.users'].browse(vals['users'])
                    if users:
                        user["username"] = users.name
                        user["firstname"] = users.first_name
                        user["lastname"] = users.last_name
                        user["phone"] = users.phone
                        user["address"] = users.address
                        user["codification"] = users.codification
                        user["role"] = users.roles
                        user["email"] = users.login


                elif self.users :
                        user["username"] = self.users.name
                        user["firstname"] = self.users.first_name
                        user["lastname"] = self.users.last_name
                        user["phone"] = self.users.phone
                        user["address"] = self.users.address
                        user["codification"] = self.users.codification
                        user["role"] = self.users.roles
                        user["email"] = self.users.login

                logging.warning("create pos (user values) ======")
                logging.warning(user)
                ek_user_emails.append(user)

                pos_users_list = {}

                if "pos_user" in vals:
                    pos_id = vals['pos_user']  # Get the ID of the 'pos' field from vals

                    pos_record = self.env['res.users'].browse(pos_id)
                    if pos_record:
                        pos_users_list["username"] = pos_record.name
                        pos_users_list["firstname"] = pos_record.first_name
                        pos_users_list["lastname"] = pos_record.last_name
                        pos_users_list["phone"] = pos_record.phone
                        pos_users_list["address"] = pos_record.address
                        pos_users_list["codification"] = pos_record.codification
                        pos_users_list["role"] = pos_record.roles
                        pos_users_list["email"] = pos_record.login


                elif self.pos_user:
                    user["username"] = self.pos_user.name
                    user["firstname"] = self.pos_user.first_name
                    user["lastname"] = self.pos_user.last_name
                    user["phone"] = self.pos_user.phone
                    user["address"] = self.pos_user.address
                    user["codification"] = self.pos_user.codification
                    user["role"] = self.pos_user.roles
                    user["email"] = self.pos_user.login

                logging.warning("create pos (pos user values) ======")
                logging.warning(pos_users_list)
                ek_user_emails.append(pos_users_list)

                data["users"] = ek_user_emails

                _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', data)

                response_cpa = requests.post(str(domain_cpa) + str(url_pos), data=json.dumps(data),
                                             headers=self.headers)
                _logger.info('\n\n\n(CREATE POS) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

                response = requests.post(str(domain) + str(url_pos), data=json.dumps(data),
                                         headers=self.headers)
                _logger.info('\n\n\n(CREATE POS) response from alsalam \n\n\n\n--->  %s\n\n\n\n', response.content)

                return rec

            else:
                rec = super(ResCompany, self).create(vals)

                return rec
