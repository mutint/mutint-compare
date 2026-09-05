from django.urls import re_path

import mutint_compare.views


urlpatterns = [
    re_path(r'^$', mutint_compare.views.mutation_table, name='compare'),
]
