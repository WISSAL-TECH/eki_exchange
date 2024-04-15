# -*- coding: utf-8 -*-
{
    'name': "eki_exchange",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'sequence': 1,
    'application': True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base_setup', 'base', 'product', 'stock', 'sale', 'purchase','crm','eki_config'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        #views
        'views/ek_product_inherit.xml'
        'views/ek_users_inherit.xml'



        #reports
        #'reports/custom_stock_report.xml',
        #'reports/facture_pro_forma_eki_click.xml',
        #'reports/facture_eki_click.xml',
        #'reports/bon_de_livraison_eki_click.xml',
        #'reports/bon_de_reception_eki_click.xml',
        #'reports/Bon_de_transfert_eki_click.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
