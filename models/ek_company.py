from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    def create(self, vals):
        if 'create_by' in vals and vals['create_by']!= 'odoo':
            logging.warning("create pos from ekiclik ======")
            logging.warning(vals)
            rec = super(ResCompany, self).create(vals)

            return rec
        else :
            logging.warning("create pos from odoo ======")
            logging.warning(vals)
            rec = super(ResCompany, self).create(vals)

            return rec


