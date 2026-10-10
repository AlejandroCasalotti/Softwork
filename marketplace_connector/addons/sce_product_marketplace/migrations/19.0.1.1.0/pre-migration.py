REMOTE_PUBLICATION_XMLIDS = (
    "view_remote_publication_wizard_form",
    "view_remote_publication_wizard_line_form",
    "action_remote_publication_wizard",
    "menu_remote_publication",
    "access_remote_publication_wizard_technical",
    "access_remote_publication_wizard_line_technical",
    "access_remote_publication_attribute_line_technical",
    "access_remote_publication_wizard_premium",
    "access_remote_publication_wizard_line_premium",
    "access_remote_publication_attribute_line_premium",
    "model_marketplace_remote_publication_wizard",
    "model_marketplace_remote_publication_wizard_line",
    "model_marketplace_remote_publication_attribute_line",
)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data AS old
           SET module = 'sce_connector_ml'
         WHERE old.module = 'sce_product_marketplace'
           AND old.name = ANY(%s)
           AND NOT EXISTS (
               SELECT 1
                 FROM ir_model_data AS current
                WHERE current.module = 'sce_connector_ml'
                  AND current.name = old.name
           )
        """,
        [list(REMOTE_PUBLICATION_XMLIDS)],
    )