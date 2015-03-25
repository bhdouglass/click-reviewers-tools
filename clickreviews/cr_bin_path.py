'''cr_bin_path.py: click bin-path'''
#
# Copyright (C) 2014-2015 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

from clickreviews.cr_common import ClickReview
import os


class ClickReviewBinPath(ClickReview):
    '''This class represents click lint reviews'''
    def __init__(self, fn, overrides=None):
        peer_hooks = dict()
        my_hook = 'bin-path'
        peer_hooks[my_hook] = dict()
        peer_hooks[my_hook]['required'] = ["apparmor"]
        peer_hooks[my_hook]['allowed'] = peer_hooks[my_hook]['required']

        ClickReview.__init__(self, fn, "bin-path", peer_hooks=peer_hooks,
                             overrides=overrides)

        # snappy yaml currently only allows specifying:
        # - name (required)
        # - exec (required)
        # - TODO: caps (optional)
        # - description (optional)
        self.required_keys = ['exec']
        self.optional_keys = ['description']

        self.bin_paths_files = dict()
        self.bin_paths = dict()
        for app in self.manifest['hooks']:
            if 'bin-path' not in self.manifest['hooks'][app]:
                #  msg("Skipped missing bin-path hook for '%s'" % app)
                continue
            if not isinstance(self.manifest['hooks'][app]['bin-path'],
               str):
                error("manifest malformed: hooks/%s/bin-path is not str"
                      % app)

            self.bin_paths = self.manifest['hooks'][app]['bin-path']
            self.bin_paths_files[app] = self._extract_bin_path(app)

    def _extract_bin_path(self, app):
        '''Get bin-path for app'''
        rel = self.manifest['hooks'][app]['bin-path']
        fn = os.path.join(self.unpack_dir, rel)
        if not os.path.exists(fn):
            error("Could not find '%s'" % rel)
        return fn

    def _check_bin_path_executable(self, app):
        '''Check that the provided path exists'''
        rel = self.manifest['hooks'][app]['bin-path']
        fn = os.path.join(self.unpack_dir, rel)
        return os.access(fn, os.X_OK)

    def _verify_required(self, my_dict, test_str):
        for app in sorted(my_dict):
            for r in self.required_keys:
                found = False
                t = 'info'
                n = '%s_required_key_%s_%s' % (test_str, r, app)
                s = "OK"
                if r in my_dict[app]:
                    if not isinstance(my_dict[app][r], str):
                        t = 'error'
                        s = "'%s' is not a string" % r
                    elif my_dict[app][r] == "":
                        t = 'error'
                        s = "'%s' is empty" % r
                    else:
                        found = True
                if not found and t != 'error':
                    t = 'error'
                    s = "Missing required field '%s'" % r
                self._add_result(t, n, s)

    def check_snappy_required(self):
        '''Check for package.yaml required fields'''
        if not self.is_snap or 'binaries' not in self.pkg_yaml:
            return
        self._verify_required(self._create_dict(self.pkg_yaml['binaries']),
                              'package_yaml')

    def _verify_optional(self, my_dict, test_str):
        for app in sorted(my_dict):
            for o in self.optional_keys:
                found = False
                t = 'info'
                n = '%s_optional_key_%s_%s' % (test_str, o, app)
                s = "OK"
                if o in my_dict[app]:
                    if o == 'stop-timeout' and \
                       not isinstance(my_dict[app][o], int):
                        t = 'error'
                        s = "'%s' is not an integer" % o
                    elif not isinstance(my_dict[app][o], str):
                        t = 'error'
                        s = "'%s' is not a string" % o
                    elif my_dict[app][o] == "":
                        t = 'error'
                        s = "'%s' is empty" % o
                    else:
                        found = True
                if not found and t != 'error':
                    s = "OK (skip missing)"
                self._add_result(t, n, s)

    def check_snappy_optional(self):
        '''Check snappy packate.yaml optional fields'''
        if not self.is_snap or 'binaries' not in self.pkg_yaml:
            return
        self._verify_optional(self._create_dict(self.pkg_yaml['binaries']),
                              'package_yaml')

    def check_path(self):
        '''Check path exists'''
        t = 'info'
        n = 'path exists'
        s = "OK"

        for app in sorted(self.bin_paths_files):
            t = 'info'
            n = 'path executable'
            s = "OK"
            if not self._check_bin_path_executable(app):
                t = 'error'
                s = "'%s' is not executable" % \
                    (self.manifest['hooks'][app]['bin-path'])
            self._add_result(t, n, s)

    def check_binary_description(self):
        '''Check package.yaml binary description'''
        if not self.is_snap or 'binaries' not in self.pkg_yaml:
            return

        my_dict = self._create_dict(self.pkg_yaml['binaries'])

        for app in sorted(my_dict):
            t = 'info'
            n = 'package_yaml_description_present_%s' % (app)
            s = 'OK'
            if 'description' not in my_dict[app]:
                s = 'OK (skip missing)'
                self._add_result('info', n, s)
                return
            self._add_result(t, n, s)

            t = 'info'
            n = 'package_yaml_description_empty_%s' % (app)
            s = 'OK'
            if len(my_dict[app]['description']) == 0:
                t = 'error'
                s = "description is empty"
            self._add_result(t, n, s)
