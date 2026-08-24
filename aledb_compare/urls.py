from django.urls import re_path

import aledb_compare.views


urlpatterns = [
    re_path(r'^$', aledb_compare.views.mutation_table, name='compare'),
]
