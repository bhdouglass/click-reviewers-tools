'''cr_security.py: click security checks'''
#
# Copyright (C) 2013-2014 Canonical Ltd.
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

from clickreviews.cr_common import ClickReview, error, warn
import clickreviews.cr_common as cr_common
import glob
import json
import os

easyprof_dir = "/usr/share/apparmor/easyprof"
if not os.path.isdir(easyprof_dir):
    error("Error importing easyprof. Please install apparmor-easyprof")
if not os.path.isdir(os.path.join(easyprof_dir, "templates/ubuntu")):
    error("Error importing easyprof. Please install apparmor-easyprof-ubuntu")

import apparmor.easyprof


class ClickReviewSecurity(ClickReview):
    '''This class represents click lint reviews'''
    def __init__(self, fn):
        ClickReview.__init__(self, fn, "security")

        self.supported_policy_versions = self._get_supported_policy_versions()

        self.all_fields = ['abstractions',
                           'author',
                           'binary',
                           'comment',
                           'copyright',
                           'name',
                           'policy_groups',
                           'policy_vendor',
                           'policy_version',
                           'read_path',
                           'template',
                           'template_variables',
                           'write_path']
        self.ignored_fields = ['author',
                               'comment',
                               'copyright',
                               'name']
        self.required_fields = ['policy_groups',
                                'policy_version']
        self.redflag_fields = ['abstractions',
                               'binary',
                               'policy_vendor',
                               'read_path',
                               'template_variables',
                               'write_path']
        self.allowed_webapp_policy_groups = ['audio',
                                             'content_exchange',
                                             'location',
                                             'networking',
                                             'video',
                                             'webview']

        self.redflag_templates = ['unconfined']
        self.extraneous_templates = ['ubuntu-sdk',
                                     'default']

        # framework policy is based on major framework version. In 13.10, there
        # was only 'ubuntu-sdk-13.10', but in 14.04, there will be several,
        # like 'ubuntu-sdk-14.04-html5', 'ubuntu-sdk-14.04-platform', etc
        self.major_framework_policy = {'ubuntu-sdk-13.10': 1.0,
                                       'ubuntu-sdk-14.04': 1.1,
                                       }

        self.security_manifests = dict()
        for app in self.manifest['hooks']:
            if 'apparmor' not in self.manifest['hooks'][app]:
                error("could not find apparmor hook for '%s'" % app)
            if not isinstance(self.manifest['hooks'][app]['apparmor'], str):
                error("manifest malformed: hooks/%s/apparmor is not str" % app)
            rel_fn = self.manifest['hooks'][app]['apparmor']
            self.security_manifests[rel_fn] = \
                self._extract_security_manifest(app)

    def _extract_security_manifest(self, app):
        '''Extract security manifest and verify it has the expected
           structure'''
        d = self.manifest['hooks'][app]['apparmor']
        fn = os.path.join(self.unpack_dir, d)
        rel_fn = self.manifest['hooks'][app]['apparmor']

        try:
            m = json.load(cr_common.open_file_read(fn))
        except Exception:
            error("Could not load '%s'. Is it properly formatted?" % rel_fn)
        mp = json.dumps(m, sort_keys=True, indent=2, separators=(',', ': '))
        if not isinstance(m, dict):
            error("'%s' malformed:\n%s" % (rel_fn, mp))
        for k in sorted(m):
            if k not in self.all_fields:
                error("'%s' malformed: unsupported field '%s':\n%s" % (rel_fn,
                                                                       k, mp))
            if k in ['abstractions', 'policy_groups', 'read_path',
                     'write_path']:
                if not isinstance(m[k], list):
                    error("'%s' malformed: '%s' is not list:\n%s" % (rel_fn,
                                                                     k, mp))
            elif k == 'template_variables':
                if not isinstance(m[k], dict):
                    error("'%s' malformed: '%s' is not dict:\n%s" % (rel_fn,
                                                                     k, mp))
            elif k == "policy_version":
                # python and Qt don't agree on the JSON output of floats that
                # are integers (ie, 1.0 vs 1). LP: #1214618
                if not isinstance(m[k], float) and not isinstance(m[k], int):
                    error("'%s' malformed: '%s' is not a JSON number:\n%s" %
                          (rel_fn, k, mp))
                if isinstance(m[k], int):
                    m[k] = float(m[k])
            else:
                if not isinstance(m[k], str):
                    error("'%s' malformed: '%s' is not str:\n%s" % (rel_fn,
                                                                    k, mp))
        return m

    def _get_policy_group_meta(self, group, meta, vendor, version):
        '''Get meta-information from the policy group'''
        cmd_args = ['--show-policy-group', '--policy-groups=%s' % group,
                    '--policy-version=%s' % version,
                    '--policy-vendor=%s' % vendor]
        (options, args) = apparmor.easyprof.parse_args(cmd_args)
        try:
            easyp = apparmor.easyprof.AppArmorEasyProfile(None, options)
            tmp = easyp.get_policygroup(group)
        except apparmor.easyprof.AppArmorException:
            warn("'%s' failed" % " ".join(cmd_args))
            return ""

        text = ""
        for line in tmp.splitlines():
            if line.startswith("# %s: " % meta):
                text = line.split(':', 1)[1].strip()
            elif text != "":
                if line.startswith("#  "):
                    text += line[2:]
                else:
                    break

        return text

    def _get_security_manifest(self, app):
        '''Get the security manifest for app'''
        if app not in self.manifest['hooks']:
            error("Could not find '%s' in click manifest" % app)
        elif 'apparmor' not in self.manifest['hooks'][app]:
            error("Could not find apparmor hook for '%s' in click manifest" %
                  app)
        f = self.manifest['hooks'][app]['apparmor']
        m = self.security_manifests[f]
        return (f, m)

    def _get_supported_policy_versions(self):
        '''Get the supported AppArmor policy versions'''
        version_dirs = sorted(glob.glob("%s/templates/ubuntu/*" %
                                        easyprof_dir))
        supported_policy_versions = []
        for d in version_dirs:
            if not os.path.isdir(d):
                continue
            try:
                supported_policy_versions.append(float(os.path.basename(d)))
            except TypeError:
                continue
        supported_policy_versions = sorted(supported_policy_versions)

        return supported_policy_versions

    def check_policy_vendor(self):
        '''Check policy_vendor'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)
            t = 'info'
            n = 'policy_vendor (%s)' % f
            s = "OK"
            if 'policy_vendor' in m and m['policy_vendor'] != "ubuntu":
                t = 'error'
                s = "policy_vendor '%s' not found" % m['policy_vendor']
            self._add_result(t, n, s)

    def check_policy_version(self):
        '''Check policy version'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)

            n = 'policy_version_exists (%s)' % f
            if 'policy_version' not in m:
                self._add_result('error', n,
                                 'could not find policy_version in manifest')
                continue

            t = 'info'
            s = "OK"
            vendor = "ubuntu"
            if 'policy_vendor' in m:
                vendor = m['policy_vendor']
            version = str(m['policy_version'])
            cmd_args = ['--list-templates', '--policy-vendor=%s' % vendor,
                        '--policy-version=%s' % version]
            (options, args) = apparmor.easyprof.parse_args(cmd_args)
            try:
                apparmor.easyprof.AppArmorEasyProfile(None, options)
            except Exception:
                t = 'error'
                s = 'could not find policy for %s/%s' % (vendor, version)
            self._add_result(t, n, s)

            highest = sorted(self.supported_policy_versions)[-1]
            t = 'info'
            n = 'policy_version_is_highest (%s, %s)' % (str(highest), f)
            s = "OK"
            if float(m['policy_version']) != highest:
                t = 'info'
                s = '%s != %s' % (str(m['policy_version']), str(highest))
            self._add_result(t, n, s)

            t = 'info'
            n = 'policy_version_matches_framework (%s)' % (f)
            s = "OK"
            found_major = False
            for k in self.major_framework_policy.keys():
                # TODO: use libclick when it is available
                if not self.manifest['framework'].startswith(k):
                    continue
                found_major = True
                if m['policy_version'] != self.major_framework_policy[k]:
                    t = 'error'
                    s = '%s != %s (%s)' % (str(m['policy_version']),
                                           self.major_framework_policy[k],
                                           self.manifest['framework'])
            if not found_major:
                t = 'error'
                s = "Invalid framework '%s'" % self.manifest['framework']
            self._add_result(t, n, s)

    def check_template(self):
        '''Check template'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)

            t = 'info'
            n = 'template_with_policy_version (%s)' % f
            s = "OK"
            if 'policy_version' not in m:
                self._add_result('error', n,
                                 'could not find policy_version in manifest')
                continue
            self._add_result(t, n, s)

            t = 'info'
            n = 'template_valid (%s)' % f
            s = "OK"
            if 'template' not in m:
                # If template not specified, we just use the default
                self._add_result(t, n, 'OK (none specified)')
                continue
            elif m['template'] in self.redflag_templates:
                t = 'error'
                s = "(MANUAL REVIEW) '%s' not allowed" % m['template']
            elif m['template'] in self.extraneous_templates:
                t = 'warn'
                s = "No need to specify '%s' template" % m['template']
            self._add_result(t, n, s)

            t = 'info'
            n = 'template_exists (%s)' % f
            s = "OK"
            vendor = "ubuntu"
            if 'policy_vendor' in m:
                vendor = m['policy_vendor']
            version = str(m['policy_version'])
            cmd_args = ['--list-templates', '--policy-vendor=%s' % vendor,
                        '--policy-version=%s' % version]
            (options, args) = apparmor.easyprof.parse_args(cmd_args)
            templates = []
            try:
                easyp = apparmor.easyprof.AppArmorEasyProfile(None, options)
                templates = easyp.get_templates()
            except Exception:
                t = 'error'
                s = 'could not find policy for %s/%s' % (vendor, version)
                self._add_result(t, n, s)
                continue
            if len(templates) < 1:
                t = 'error'
                s = 'could not find templates'
                self._add_result(t, n, s)
                continue

            # If we got here, we can see if a valid template was specified
            found = False
            for i in templates:
                if os.path.basename(i) == m['template']:
                    found = True
                    break
            if not found:
                t = 'error'
                s = "specified unsupported template '%s'" % m['template']

            self._add_result(t, n, s)

    def check_policy_groups_webapps(self):
        '''Check policy_groups for webapps'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)
            t = 'info'
            n = 'policy_groups_webapp (%s)' % f
            s = "OK"
            webapp_template = "ubuntu-webapp"
            if 'template' not in m or m['template'] != webapp_template:
                # self._add_result(t, n, s)
                continue
            if 'policy_groups' not in m or \
               'networking' not in m['policy_groups']:
                self._add_result('error', n,
                                 "required group 'networking' not found")
                continue
            bad = []
            for p in m['policy_groups']:
                if p not in self.allowed_webapp_policy_groups:
                    bad.append(p)
            if len(bad) > 0:
                t = 'error'
                s = "found unusual policy groups: %s" % ", ".join(bad)
            self._add_result(t, n, s)

            t = 'info'
            n = 'policy_groups_webapp_webview (%s)' % f
            s = "OK"
            if self.manifest['framework'] == "ubuntu-sdk-13.10":
                s = "SKIPPED (webview not available in 13.10)"
            elif 'webview' not in m['policy_groups']:
                t = 'warn'
                s = "'webview' not specified. Webapp may not function"

            self._add_result(t, n, s)

    def check_policy_groups(self):
        '''Check policy_groups'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)

            t = 'info'
            n = 'policy_groups_exists (%s)' % f
            if 'policy_groups' not in m:
                # If template not specified, we just use the default
                self._add_result('warn', n, 'no policy groups specified')
                continue
            elif 'policy_version' not in m:
                self._add_result('error', n,
                                 'could not find policy_version in manifest')
                continue

            s = "OK"
            vendor = "ubuntu"
            if 'policy_vendor' in m:
                vendor = m['policy_vendor']
            version = str(m['policy_version'])
            cmd_args = ['--list-policy-groups', '--policy-vendor=%s' % vendor,
                        '--policy-version=%s' % version]
            (options, args) = apparmor.easyprof.parse_args(cmd_args)
            policy_groups = []
            try:
                easyp = apparmor.easyprof.AppArmorEasyProfile(None, options)
                policy_groups = easyp.get_policy_groups()
            except Exception:
                t = 'error'
                s = 'could not find policy for %s/%s' % (vendor, version)
                self._add_result(t, n, s)
                continue
            if len(policy_groups) < 1:
                t = 'error'
                s = 'could not find policy groups'
                self._add_result(t, n, s)
                continue
            self._add_result(t, n, s)

            # Check for duplicates
            t = 'info'
            n = 'policy_groups_duplicates (%s)' % f
            s = 'OK'
            tmp = []
            for p in m['policy_groups']:
                if m['policy_groups'].count(p) > 1 and p not in tmp:
                    tmp.append(p)
                if len(tmp) > 0:
                    tmp.sort()
                    t = 'error'
                    s = 'duplicate policy groups found: %s' % ", ".join(tmp)
            self._add_result(t, n, s)

            # If we got here, we can see if valid policy groups were specified
            for i in m['policy_groups']:
                t = 'info'
                n = 'policy_groups_valid (%s)' % i
                s = 'OK'

                # SDK will leave and empty policy group, report but don't
                # deny
                if i == "":
                    t = 'error'
                    s = 'found empty policy group'
                    self._add_result(t, n, s)
                    continue

                found = False
                for j in policy_groups:
                    if i == os.path.basename(j):
                        found = True
                        break
                if not found:
                    t = 'error'
                    s = "unsupported policy_group '%s'" % i
                self._add_result(t, n, s)

                if found:
                    t = 'info'
                    n = 'policy_groups_safe (%s)' % i
                    s = 'OK'
                    usage = self._get_policy_group_meta(i, "Usage",
                                                        vendor, version)
                    if usage != "common":
                        desc = self._get_policy_group_meta(i, "Description",
                                                           vendor, version)
                        t = 'error'
                        s = "(MANUAL REVIEW) %s policy group " % usage + \
                            "'%s': %s" % (i, desc)
                    self._add_result(t, n, s)

    def check_ignored(self):
        '''Check ignored fields'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)

            t = 'info'
            n = 'ignored_fields (%s)' % f
            s = "OK"
            found = []
            for i in self.ignored_fields:
                if i in m:
                    found.append(i)

            if len(found) > 0:
                t = 'warn'
                s = "found ignored fields: %s" % ", ".join(found)
            self._add_result(t, n, s)

    def check_redflag(self):
        '''Check redflag fields'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)

            t = 'info'
            n = 'redflag_fields (%s)' % f
            s = "OK"
            found = []
            for i in self.redflag_fields:
                if i in m:
                    found.append(i)

            if len(found) > 0:
                t = 'error'
                s = "found redflagged fields (needs human review): %s" % \
                    ", ".join(found)
            self._add_result(t, n, s)

    def check_required(self):
        '''Check required fields'''
        for app in sorted(self.manifest['hooks']):
            (f, m) = self._get_security_manifest(app)

            t = 'info'
            n = 'ignored_fields (%s)' % f
            s = "OK"
            not_found = []
            for i in self.required_fields:
                if i not in m:
                    not_found.append(i)

            if len(not_found) > 0:
                t = 'error'
                s = "missing required fields: %s" % ", ".join(not_found)
            self._add_result(t, n, s)
