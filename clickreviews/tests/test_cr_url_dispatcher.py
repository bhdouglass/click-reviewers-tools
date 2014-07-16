'''test_cr_url dispatcher.py: tests for the cr_url_dispatcher module'''
#
# Copyright (C) 2014 Canonical Ltd.
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

from clickreviews.cr_url_dispatcher import ClickReviewUrlDispatcher
import clickreviews.cr_tests as cr_tests


class TestClickReviewUrlDispatcher(cr_tests.TestClickReview):
    """Tests for the lint review tool."""
    def setUp(self):
        # Monkey patch various file access classes. stop() is handled with
        # addCleanup in super()
        cr_tests.mock_patch()
        super()

    def test_check_required(self):
        '''Test check_required() - has protocol'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_required()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_required_empty_value(self):
        '''Test check_required() - empty protocol'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="")
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_required()
        r = c.click_report
        expected_counts = {'info': 0, 'warn': 0, 'error': 1}
        self.check_results(r, expected_counts)

    def test_check_required_bad_value(self):
        '''Test check_required() - bad protocol'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value=[])
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_required()
        r = c.click_report
        expected_counts = {'info': 0, 'warn': 0, 'error': 1}
        self.check_results(r, expected_counts)

    def test_check_required_multiple(self):
        '''Test check_required() - multiple'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com",
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_required()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_required_multiple(self):
        '''Test check_required() - multiple with nonexistent'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com",
                                     append=True)
        self.set_test_url_dispatcher(self.default_appname,
                                     key="nonexistent",
                                     value="foo",
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_required()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_optional_none(self):
        '''Test check_optional() - protocol only'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_optional()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_optional_domain_suffix_empty(self):
        '''Test check_optional() - with empty domain-suffix'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="",
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_optional()
        r = c.click_report
        expected_counts = {'info': 0, 'warn': 0, 'error': 1}
        self.check_results(r, expected_counts)

    def test_check_optional_domain_suffix_bad(self):
        '''Test check_optional() - with bad domain-suffix'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value=[],
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_optional()
        r = c.click_report
        expected_counts = {'info': 0, 'warn': 0, 'error': 1}
        self.check_results(r, expected_counts)

    def test_check_optional_domain_suffix_nonexistent(self):
        '''Test check_optional() - with domain-suffix plus nonexistent'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com",
                                     append=True)
        self.set_test_url_dispatcher(self.default_appname,
                                     key="nonexistent",
                                     value="foo",
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_optional()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_optional_domain_suffix_without_protocol(self):
        '''Test check_optional() - with domain-suffix, no protocol'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com")
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_optional()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_optional_domain_suffix_without_protocol2(self):
        '''Test check_optional() - with domain-suffix, nonexistent, no
           protocol'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com",
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_optional()
        r = c.click_report
        expected_counts = {'info': 1, 'warn': 0, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_unknown(self):
        '''Test check_unknown()'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="nonexistent",
                                     value="foo")
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_unknown()
        r = c.click_report
        expected_counts = {'info': 0, 'warn': 1, 'error': 0}
        self.check_results(r, expected_counts)

    def test_check_unknown_multiple(self):
        '''Test check_unknown() - multiple with nonexistent'''
        self.set_test_url_dispatcher(self.default_appname,
                                     key="protocol",
                                     value="some-protocol")
        self.set_test_url_dispatcher(self.default_appname,
                                     key="domain-suffix",
                                     value="example.com",
                                     append=True)
        self.set_test_url_dispatcher(self.default_appname,
                                     key="nonexistent",
                                     value="foo",
                                     append=True)
        c = ClickReviewUrlDispatcher(self.test_name)
        c.check_unknown()
        r = c.click_report
        expected_counts = {'info': 0, 'warn': 1, 'error': 0}
        self.check_results(r, expected_counts)
