# -*- coding: utf-8 -*-


def pre_init_deduplicate_ml_question_channels(env):
    """Keeps the latest relay record for legacy duplicated ML questions."""
    env.cr.execute("SELECT to_regclass('public.ml_question_channel')")
    if not env.cr.fetchone()[0]:
        return
    env.cr.execute(
        """
        DELETE FROM ml_question_channel duplicate
        USING ml_question_channel current
        WHERE duplicate.account_id = current.account_id
          AND duplicate.ml_question_id = current.ml_question_id
          AND duplicate.id < current.id
        """
    )