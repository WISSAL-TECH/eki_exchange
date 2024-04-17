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


class ResUsers(models.Model):
    _inherit = 'res.users'

    ek_user = fields.Boolean(string="Utilisateur ekiclik", default=False)
    first_name = fields.Char("Nom")
    last_name = fields.Char("Prénom")
    phone = fields.Char("Téléphone")
    address = fields.Char("Address")
    codification = fields.Char("Codification")
    roles = fields.Selection([
        ('ROLE_CREDIT_ANALYST_EK', 'Credit analyst'),
        ('ROLE_POS_EK', 'Pos')
    ], string="Roles")

    @api.onchange('ek_user')
    def _onchange_ek_user(self):
        if self.ek_user:
            self._fields['codification'].required = True
            self._fields['first_name'].required = True
            self._fields['last_name'].required = True
            self._fields['phone'].required = True
            self._fields['address'].required = True
            self._fields['roles'].required = True
        else:
            self._fields['codification'].required = False
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}
    def _check_codification_length(self, vals):
        codification = vals.get('codification')
        if codification and len(codification) != 21:
            raise UserError("Codification must be 21 characters long.")

    @api.model
    def create(self, vals):
        self._check_codification_length(vals)

        rec = super(ResUsers, self).create(vals)
        if "ek_user" in vals and vals.get('ek_user') == True:

            logging.warning("create user ======")
            logging.warning(vals)

            domain = ""
            domain_cpa = ""
            config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
            if config_settings:
                domain = config_settings.domain
                domain_cpa = config_settings.domain_cpa
            url_users = "/api/odoo/users"

            data = {
                "username": vals.get('name'),
                "firstname": vals.get('first_name'),
                "lastname": vals.get('last_name'),
                "phone": vals.get('phone'),
                "address": vals.get('address'),
                "codification": vals.get('codification'),
                "role": vals.get('roles'),
                "email": vals.get('login')
            }

            _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', data)

            response_cpa = requests.post(str(domain_cpa) + str(url_users), data=json.dumps(data),
                                         headers=self.headers)
            _logger.info('\n\n\n(CREATE user) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

            response = requests.post(str(domain) + str(url_users), data=json.dumps(data),
                                     headers=self.headers)
            _logger.info('\n\n\n(CREATE user) response from alsalam \n\n\n\n--->  %s\n\n\n\n', response.content)

            return rec

        else:

            return rec

    def write(self, vals):
        self._check_codification_length(vals)

        rec = super(ResUsers, self).write(vals)
        if "ek_user" in vals and vals.get('ek_user') == True:

            logging.warning("update user ======")
            logging.warning(vals)

            domain = ""
            domain_cpa = ""
            config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
            if config_settings:
                domain = config_settings.domain
                domain_cpa = config_settings.domain_cpa
            url_users = "/api/odoo/users"

            data = {
                "username": vals.get('name') if 'name' in vals else rec.name,
                "firstname": vals.get('first_name') if 'first_name' in vals else rec.first_name,
                "lastname": vals.get('last_name') if 'last_name' in vals else rec.last_name,
                "phone": vals.get('phone') if 'phone' in vals else rec.phone,
                "address": vals.get('address') if 'phone' in vals else rec.phone,
                "codification": vals.get('codification') if 'codification' in vals else rec.codification,
                "role": vals.get('roles') if 'roles' in vals else rec.roles,
                "email": vals.get('login') if 'login' in vals else rec.login
            }

            _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', data)

            response_cpa = requests.post(str(domain_cpa) + str(url_users), data=json.dumps(data),
                                         headers=self.headers)
            _logger.info('\n\n\n(CREATE user) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

            response = requests.post(str(domain) + str(url_users), data=json.dumps(data),
                                     headers=self.headers)
            _logger.info('\n\n\n(CREATE user) response from alsalam \n\n\n\n--->  %s\n\n\n\n', response.content)

            return rec

        else:

            return rec
