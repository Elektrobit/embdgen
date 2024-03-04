# SPDX-License-Identifier: GPL-3.0-only

from  embdgen.core.content_generator import Factory

def test_factory():
    f_types = Factory().types()
    assert 'split_archive' in f_types
