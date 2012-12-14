"""
Test module for the configuration generator.
"""

import StringIO, sys, os, datetime, tempfile
from nose.tools import assert_raises

from slam import generator, models

SLAM_HDR1 = (" This section will be automatically generated by SLAM any"
    + " manual change will\n")
SLAM_HDR2 = " be overwritten on the next generation of this file.\n"
SLAM_FTR = " END of section automatically generated by SLAM\n"

def _strstream(str_):
    r, w = os.pipe()
    r = os.fdopen(r, "r")
    w = os.fdopen(w, "w")
    w.write(str_)
    w.close()
    return r

def test_general():
    handle, hdrpath = tempfile.mkstemp()
    filobj = open(hdrpath, "w")
    filobj.write("header1\nheader2\n")
    filobj.close()
    handle, ftrpath = tempfile.mkstemp()
    filobj = open(ftrpath, "w")
    filobj.write("footer1\nfooter2\n")
    filobj.close()

    out = StringIO.StringIO()
    saved_stdout = sys.stdout
    sys.stdout = out

    conf = generator.DhcpdConfig.create(name="newgen",
        outputfile="-", header=hdrpath, footer=ftrpath)
    assert str(conf) == "newgen (dhcp), output file: \"-\""
    conf.createconf([])
    assert(out.getvalue() == "header1\nheader2\n" + "\n#" + SLAM_HDR1
        + "#" + SLAM_HDR2 + "#" + SLAM_FTR + "footer1\nfooter2\n")

    conf.save()
    conf = generator.DhcpdConfig.objects.get(name="newgen")
    out = StringIO.StringIO()
    sys.stdout = out
    conf.createconf([])
    assert conf.headerfile == hdrpath
    assert conf.footerfile == ftrpath
    assert conf.outputfile == "-"
    assert(out.getvalue() == "header1\nheader2\n" + "\n#" + SLAM_HDR1
        + "#" + SLAM_HDR2 + "#" + SLAM_FTR + "footer1\nfooter2\n")

    sys.stdout = saved_stdout
    os.unlink(hdrpath)
    os.unlink(ftrpath)


def test_update_soa():
    assert(generator._update_soa("@ 6H IN SOA foo bar 1970032809 a b c d\n")
        == "@ 6H IN SOA foo bar "
            + datetime.date.today().strftime("%Y%m%d") + "01 a b c d\n")
    assert(generator._update_soa("@ 6H IN SOA foo bar " +
    datetime.date.today().strftime("%Y%m%d") + "09 a b c d\n")
        == "@ 6H IN SOA foo bar "
            + datetime.date.today().strftime("%Y%m%d") + "10 a b c d\n")

    assert_raises(ValueError, generator._update_soa,
        "@ 6H IN SOA foo bar 201209 a b c d\n")
    assert_raises(ValueError, generator._update_soa,
        "@ 6H IN SOA foo bar barfoo a b c d\n")
    assert_raises(ValueError, generator._update_soa, "@ 6H IN SOA foo bar " +
        datetime.date.today().strftime("%Y%m%d") + "99 a b c d\n")


def test_bind():
    hdr = _strstream("stuff\n@ 1D IN SOA foo bar " +
        datetime.date.today().strftime("%Y%m%d") + "02 a b c d\n")
    out = StringIO.StringIO()

    conf = generator.BindConfig.create(outputfile=None)
    conf.output = out
    conf.header = hdr
    conf.footer = None

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")
    addr1 = models.Address(addr="addr", pool=models.Pool(dns_record="A"))
    addr2 = models.Address(addr="rdda", pool=models.Pool(dns_record="A"))
    addr3 = models.Address(addr="addr2", pool=models.Pool(dns_record="AAAA"))
    conf.createconf([(host1, [addr1, addr2], []), (host2, [addr3], [])])

    assert(out.getvalue() == "stuff\n@ 1D IN SOA foo bar "
        + datetime.date.today().strftime("%Y%m%d") + "03 a b c d\n\n;"
        + SLAM_HDR1 + ";" + SLAM_HDR2
        + "host1\t1D\tIN\tA\taddr\n"
        + "host1\t1D\tIN\tA\trdda\n"
        + "host2\t1D\tIN\tAAAA\taddr2\n"
        + ";" + SLAM_FTR)


def test_revbind():
    conf = generator.RevBindConfig.create(outputfile=None, timeout="6H")
    out = StringIO.StringIO()
    conf.output = out
    conf.header = None
    conf.footer = None

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")
    addr1 = models.Address(addr="192.168.50.30",
        pool=models.Pool(addr_range_type="ip4", dns_record="A"))
    addr2 = models.Address(addr="fe80:1234:5678:9abc:def0:1234:5678:9abc",
        pool=models.Pool(addr_range_type="ip6", dns_record="AAAA"))
    conf.createconf([(host1, [addr1], []), (host2, [addr2], [])])

    print("@@@" + out.getvalue() + "@@@")
    assert(out.getvalue() == "\n;" + SLAM_HDR1 + ";" + SLAM_HDR2
        + "30.50.168.192.in-addr.arpa.\t6H\tIN\tPTR\thost1\n"
        + "c.b.a.9.8.7.6.5.4.3.2.1.0.f.e.d.c.b.a.9.8.7.6.5.4.3.2.1.0.8.e.f"
        + ".ip6.arpa.\t6H\tIN\tPTR\thost2\n"
        + ";" + SLAM_FTR)


def test_dhcp():
    conf = generator.DhcpdConfig.create(outputfile=None, domain="foo.example")
    out = StringIO.StringIO()
    conf.output = out

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")
    addr1 = models.Address(addr="192.168.50.30", macaddr="01:12:34:56:78:9a")
    addr2 = models.Address(addr="192.168.42.137")
    conf.createconf([(host1, [addr1], []), (host2, [addr2], [])])

    assert(out.getvalue() == "\n#" + SLAM_HDR1 + "#" + SLAM_HDR2
        + "option domain-name \"foo.example\";\n"
        + "host host1 { hardware ethernet 01:12:34:56:78:9a; "
        + "fixed-address host1; }\n"
        + "host host2 { fixed-address host2; }\n"
        + "#" + SLAM_FTR)


def test_quattor():
    conf = generator.QuattorConfig.create(outputfile=None)
    out = StringIO.StringIO()
    conf.output = out

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")
    addr1 = models.Address(addr="192.168.50.30", macaddr="01:12:34:56:78:9a")
    addr2 = models.Address(addr="192.168.42.137")
    conf.createconf([(host1, [addr1], []), (host2, [addr2], [])])

    assert(out.getvalue() == "\n#" + SLAM_HDR1 + "#" + SLAM_HDR2
        + 'escape("host1"),"192.168.50.30",\n'
        + 'escape("host2"),"192.168.42.137",\n'
        + "#" + SLAM_FTR)


def test_update():
    handle, path = tempfile.mkstemp()
    orig = open(path, "r+")
    orig.write("HEADER\n\n;" + SLAM_HDR1 + ";" + SLAM_HDR2
        + "useless content\n;"+ SLAM_FTR + "FOOTER\n")
    orig.flush()
    orig.seek(0)
    conf = generator.BindConfig.create(outputfile=None)
    conf.output = orig

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")
    addr1 = models.Address(addr="addr", pool=models.Pool(dns_record="A"))
    addr2 = models.Address(addr="rdda", pool=models.Pool(dns_record="A"))
    addr3 = models.Address(addr="addr2", pool=models.Pool(dns_record="AAAA"))
    conf.updateconf([(host1, [addr1, addr2], []), (host2, [addr3], [])])

    orig.seek(0)
    res = orig.read()
    assert(res == "HEADER\n\n;" + SLAM_HDR1 + ";" + SLAM_HDR2
        + "host1\t1D\tIN\tA\taddr\n"
        + "host1\t1D\tIN\tA\trdda\n"
        + "host2\t1D\tIN\tAAAA\taddr2\n"
        + ";" + SLAM_FTR + "FOOTER\n")

    orig.close()
    os.unlink(path)

def _generator_checkfile(cls, content):
    handle, path = tempfile.mkstemp()
    checkf = open(path, "w")
    checkf.write(content)
    checkf.close()

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")

    conf = cls.create(outputfile="-")
    dup = conf.createconf([(host1, [], []), (host2, [], [])])
    assert len(dup) == 0

    conf = cls.create(outputfile="-", checkfile=[path])
    dup = conf.createconf([(host1, [], []), (host2, [], [])])
    assert len(dup) == 1

    os.unlink(path)

def test_checkfile():
    handle, path1 = tempfile.mkstemp()
    checkf1 = open(path1, "w")
    handle, path2 = tempfile.mkstemp()
    checkf2 = open(path2, "w")

    checkf1.write("host1\t1d\tin\ta\taddr\n"
        + "host1\t1d\tin\ta\trdda\n"
        + "host2\t1d\tin\taaaa\taddr2\n")
    checkf2.write("host142\t1d\tin\ta\taddr\n"
        + "42host1\t1d\tin\ta\trdda\n"
        + "host\t1d\tin\taaaa\taddr2\n")
    checkf1.close()
    checkf2.close()

    host1 = models.Host(name="host1")
    host2 = models.Host(name="host2")

    conf = generator.BindConfig.create(outputfile="-")
    conf.createconf([(host1, [], []), (host2, [], [])])

    conf = generator.BindConfig.create(outputfile="-", checkfile=[path2])
    dup = conf.createconf([(host1, [], []), (host2, [], [])])
    assert len(dup) == 0

    conf = generator.BindConfig.create(outputfile="-", checkfile=[path1])
    dup = conf.createconf([(host1, [], []), (host2, [], [])])
    assert len(dup) == 3

    conf = generator.BindConfig.create(outputfile="-",
        checkfile=[path1, path2])
    dup = conf.createconf([(host1, [], []), (host2, [], [])])
    assert len(dup) == 3

    os.unlink(path1)
    os.unlink(path2)

    # other generators
    _generator_checkfile(generator.RevBindConfig,
        "117.103.168.192.in-addr.arpa. 1D IN PTR test.domain.\n"
        + "118.103.168.192.in-addr.arpa. 1D IN PTR host1.domain.")
    _generator_checkfile(generator.DhcpdConfig,
        "host test { fixed-address test; }\n"
        + "host host1 { fixed-address host1; }")
    _generator_checkfile(generator.QuattorConfig,
        "escape(\"test\"),\"1.2.3.4\"\n"
        + "escape(\"host2\"),\"1.2.2.2\"")
