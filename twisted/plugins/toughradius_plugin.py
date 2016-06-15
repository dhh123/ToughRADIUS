# coding: utf-8

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import imp
import sys
import types
import sys,signal,click
import platform as pf
from twisted.internet import reactor
from twisted.python import log
from toughlib import config as iconfig
from toughlib import dispatch,logger,utils
from toughlib.dbengine import get_engine
from toughradius.manage import settings
from toughradius.manage.settings import redis_conf
from toughradius.common import log_trace
from twisted.application import internet
from twisted.application import service
from twisted.plugin import IPlugin
from twisted.python import usage
from twisted.python import reflect
from zope.interface import implements

try:
    from twisted.internet import ssl
except ImportError:
    ssl_support = False
else:
    ssl_support = True


class Options(usage.Options):
    # The reason for having app=x and ssl-app=y is to be able to have
    # different URI routing on HTTP and HTTPS.
    # Example: A login handler that only exists in HTTPS.
    optParameters = [
        ["debug", "d", "debug option"],
        ["config", "c", "/etc/toughradius.json", "config file"],
        ["service", "s", "all", "service name [all, manage, radiusd]"],
    ]

    def parseArgs(self, *args):
        if args:
            self["filename"] = args[0]


class ServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = "toughradius"
    description = "A high performance radius server"
    options = Options

    def setup_logger(self,config):
        syslog = logger.Logger(config,'radius')
        dispatch.register(syslog)
        # log.startLoggingWithObserver(syslog.emit, setStdout=0)

    def update_timezone(self,config):
        if 'TZ' not in os.environ:
            os.environ["TZ"] = config.system.tz
        try:time.tzset()
        except:pass

    def start_all(self,conf,service,debug=False):
        from toughradius.manage import httpd
        from toughradius.manage import radiusd
        from toughradius.manage import taskd
        from toughlib.redis_cache import CacheManager
        config = iconfig.find_config(conf)
        self.update_timezone(config)
        self.setup_logger(config)
        if debug:
            config.system.debug = True
        dbengine = get_engine(config)
        cache = CacheManager(redis_conf(config),cache_name='RadiusCache')
        aes = utils.AESCipher(key=config.system.secret)
        httpd.run(config,dbengine,cache=cache,aes=aes,service=service)
        radiusd.run_auth(config,service=service)
        radiusd.run_acct(config,service=service)
        taskd.run(config,dbengine,cache=cache,aes=aes,standalone=True,service=service)
        radiusd.run_worker(config,dbengine,cache=cache,aes=aes,standalone=True,service=service)

    def start_radiusd(self,conf,service,debug=False):
        from toughradius.manage import radiusd
        from toughlib.redis_cache import CacheManager
        config = iconfig.find_config(conf)
        self.update_timezone(config)
        self.setup_logger(config)
        if debug:
            config.system.debug = True
        dbengine = get_engine(config)
        cache = CacheManager(redis_conf(config),cache_name='RadiusCache')
        aes = utils.AESCipher(key=config.system.secret)
        radiusd.run_auth(config,service=service)
        radiusd.run_acct(config,service=service)
        # radiusd.run_worker(config,dbengine,cache=cache,aes=aes,standalone=True,service=service)

    def start_manage(self,conf,service,debug=False):
        from toughradius.manage import httpd
        from toughradius.manage import taskd
        from toughlib.redis_cache import CacheManager
        config = iconfig.find_config(conf)
        self.update_timezone(config)
        self.setup_logger(config)
        if debug:
            config.system.debug = True
        dbengine = get_engine(config)
        cache = CacheManager(redis_conf(config),cache_name='RadiusCache')
        aes = utils.AESCipher(key=config.system.secret)
        httpd.run(config,dbengine,cache=cache,aes=aes,service=service)
        taskd.run(config,dbengine,cache=cache,aes=aes,standalone=True,service=service)

    def makeService(self, options):
        srv = service.MultiService()
        if options["service"] == 'all':
            self.start_all(options["config"], srv, options["debug"])
        if options["service"] == 'manage':
            self.start_manage(options["config"], srv, options["debug"])
        if options["service"] == 'radiusd':
            self.start_radiusd(options["config"], srv, options["debug"])
        return srv

serviceMaker = ServiceMaker()










