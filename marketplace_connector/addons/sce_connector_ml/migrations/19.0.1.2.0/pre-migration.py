def migrate(cr, version):
    cr.execute(
        """
        SELECT id, name, model, res_id
          FROM ir_model_data
         WHERE module = 'sce_product_marketplace'
         ORDER BY id
        """
    )
    records = cr.fetchall()
    for old_id, name, model, res_id in records:
        cr.execute(
            """
            SELECT id, model, res_id
              FROM ir_model_data
             WHERE module = 'sce_connector_ml' AND name = %s
            """,
            [name],
        )
        current = cr.fetchone()
        if current:
            if current[1:] != (model, res_id):
                raise RuntimeError(
                    "Cannot migrate XML ID sce_product_marketplace.%s: "
                    "sce_connector_ml.%s already points to another record." % (name, name)
                )
            cr.execute("DELETE FROM ir_model_data WHERE id = %s", [old_id])
        else:
            cr.execute(
                "UPDATE ir_model_data SET module = 'sce_connector_ml' WHERE id = %s",
                [old_id],
            )