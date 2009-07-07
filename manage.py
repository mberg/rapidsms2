#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import sys, os
sys.path.append(os.path.join(os.getcwd(),'lib'))
PIDFILE = '/var/run/rapidsms_%sd.pid' % sys.argv[1]

import rapidsms

if __name__ == "__main__":
    pid = os.getpid()
    open(PIDFILE, 'w').write("%d" % pid)
    print pid
    rapidsms.manager.start(sys.argv)
