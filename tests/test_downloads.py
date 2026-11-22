#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import io
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import downloads

class Downloads(unittest.TestCase):
    def test_rate_limit_honors_server_delay_before_retry(self):
        error=urllib.error.HTTPError('https://example.invalid/icon',429,'rate limited',{'Retry-After':'2'},None)
        with patch.object(downloads.urllib.request,'urlopen',side_effect=[error,io.BytesIO(b'asset')]) as opened,patch.object(downloads.time,'sleep') as sleep:
            with downloads.open_url('https://example.invalid/icon') as response:self.assertEqual(response.read(),b'asset')
            sleep.assert_called_once_with(2);self.assertEqual(opened.call_count,2)
    def test_long_server_delay_stops_without_early_retry(self):
        error=urllib.error.HTTPError('https://example.invalid',429,'rate limited',{'Retry-After':'600'},None)
        with patch.object(downloads.urllib.request,'urlopen',side_effect=error) as opened,patch.object(downloads.time,'sleep') as sleep:
            with self.assertRaises(downloads.DownloadError):downloads.open_url('https://example.invalid')
            self.assertEqual(opened.call_count,1);sleep.assert_not_called()
    def test_permission_errors_are_not_retried(self):
        error=urllib.error.HTTPError('https://example.invalid',403,'denied',{},None)
        with patch.object(downloads.urllib.request,'urlopen',side_effect=error) as opened,patch.object(downloads.time,'sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError):downloads.open_url('https://example.invalid')
            self.assertEqual(opened.call_count,1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
