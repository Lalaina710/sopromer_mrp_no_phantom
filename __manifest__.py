{
    'name': 'SOPROMER MRP No Phantom',
    'version': '18.0.1.1.0',
    'category': 'Manufacturing',
    'summary': 'Bloque la creation de stock fantome via MO (check stock dispo a la confirmation + composant non consomme + conservation masse)',
    'author': 'SOPROMER',
    'website': 'https://github.com/Lalaina710/sopromer_mrp_no_phantom',
    'license': 'LGPL-3',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'data/res_config_parameters.xml',
        'views/res_config_settings_view.xml',
        'views/mrp_bom_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
