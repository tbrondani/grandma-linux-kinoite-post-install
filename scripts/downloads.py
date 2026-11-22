#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded retries for transient public asset downloads; honor Retry-After."""
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import time
import urllib.error
import urllib.request

class DownloadError(RuntimeError):pass


def retry_delay(value,attempt):
    if value:
        try:
            if value.strip().isdigit():return float(value.strip())
            date=parsedate_to_datetime(value)
            if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
            return max(0,(date-datetime.now(timezone.utc)).total_seconds())
        except (ValueError,TypeError,OverflowError):pass
    return 10*(2**attempt)


def open_url(url,timeout=30):
    request=urllib.request.Request(url,headers={'User-Agent':'GrandmaLinux/0.1 (public asset download)'}) if isinstance(url,str) else url
    for attempt in range(3):
        try:return urllib.request.urlopen(request,timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code not in {429,502,503,504}:raise
            delay=retry_delay(error.headers.get('Retry-After') if error.headers else None,attempt)
            if attempt==2 or delay>120:
                raise DownloadError('Download server is temporarily unavailable (HTTP '+str(error.code)+'). Retry later; installed data were retained.') from None
            print('Download server requested a pause; retrying in '+str(round(delay))+' seconds.',flush=True)
            time.sleep(delay)
        except (TimeoutError,urllib.error.URLError) as error:
            reason=getattr(error,'reason',error)
            if not isinstance(reason,(TimeoutError,ConnectionResetError)):raise
            if attempt==2:raise DownloadError('Download timed out. Retry later; installed data were retained.') from None
            time.sleep(10*(2**attempt))
