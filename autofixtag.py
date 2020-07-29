import os
import re

__old_gitv = 'xxxxxxxx'
__ignores = [".*/Editor/.*"]

print(
    "此工具会将本地修改还原到HEAD 版本，提前commit代码。确定无误后注释下面一行代码重新执行工具。\n(This will revert to HEAD.Backup you code and uncomment next line.)")


def is_ignored(one):
    for x in __ignores:
        if re.match(x, one):
            return True
    return False


__tags = ["[^\n]*Interpret]", "[^\n]*Patch]"]


def decodeall(bts, igerr=False):
    res = None
    error = ""
    coding = "utf-8"
    try:
        res = bts.decode(coding)
    except Exception as e:
        error = e
    if not res:
        try:
            coding = "gb18030"
            res = bts.decode(coding)
        except Exception as e:
            error = e
    if not res and igerr:
        coding = "utf-8"
        res = bts.decode(coding, "ignore")
    if not res:
        print(error)
    return res, coding


def read_content(path):
    with open(path, 'rb') as fs:
        content, coding = decodeall(fs.read())

    for tag in __tags:
        fits = re.findall(tag, content)
        if len(fits) > 0:
            for x in fits:
                content = content.replace(x, "")
    return content.replace("\r\n", "\n"), coding


def unpack(content):
    head = ''
    enums = {}
    nenum = ''
    enumb = 0
    structs = {}
    nstruct = ''
    structb = 0
    classes = {}
    fields = {}
    properties = {}
    methods = {}
    classb = 0
    methodb = 0
    ncls = ''
    nmethod = ''
    nprop = ''
    propb = 0
    nfield = ''
    fieldb = 0
    incomment = False
    sps = content.split("\n")

    def checkcls(tp, line, numb, dic, n, bs, be):
        isnew = False
        clss = re.findall('(?<=\s%s\s)\w+' % tp, line)
        if len(clss) > 0:
            n = clss[0]
            dic[n] = ""
            isnew = True
        if n:
            if bs:
                for x in line:
                    if "{" == x:
                        numb += 1
            dic[n] += line
            if be:
                for x in line:
                    if "}" == x:
                        numb -= 1
                if numb == 0:
                    n = ""
            if n:
                dic[n] += '\n'
        return n, numb, isnew

    for i in range(0, len(sps)):
        line = sps[i]

        if not incomment:
            incomment = "/*" in line
        else:
            if "*/" in line:
                incomment = False
        iscomment = "*/" in line or len(re.findall(r'<param.*param>', line)) > 0 or "///" in line or len(re.findall(r"\n\s*//.*", "\n" + line)) > 0
        fline = re.findall(r"\w+\s*//", line)
        fline = fline[0] if len(fline) > 0 else line
        blockstart = "{" in fline and not incomment and not iscomment
        blockend = "}" in fline and not incomment and not iscomment
        if not incomment:
            ncls, classb, aisnew = checkcls("class", line, classb, classes, ncls, blockstart, blockend)
            nstruct, structb, bisnew = checkcls("struct", line, structb, structs, nstruct, blockstart, blockend)
            nenum, enumb, cisnew = checkcls("enum", line, enumb, enums, nenum, blockstart, blockend)
            isnew = aisnew or bisnew or cisnew
        if not ncls and not nstruct and not nenum and "}" not in line:
            head += line + "\n"
        if ncls or nstruct:
            ntp = ncls if ncls else nstruct

            if not nprop and not nmethod and ";" not in line and not iscomment and not incomment:
                mets = re.findall(r'(?<=\s)[\w<>]+(?=[\s]*\()', line)
                if len(mets) > 0 and mets[0]:
                    nmethod = mets[0]
                    if ntp not in methods:
                        methods[ntp] = {}
                    methods[ntp][nmethod] = ""
            if nmethod:
                if blockstart:
                    methodb += 1
                methods[ntp][nmethod] += line + "\n"
                if blockend:
                    methodb -= 1
                    if methodb == 0:
                        nmethod = ""

            if not nmethod and not isnew:
                istag = False
                tags = re.findall(r'\s\[[^\n\]]*\]', line)
                if len(tags) > 0:
                    tl = line
                    for t in tags:
                        tl = tl.replace(t, "")
                    istag = len(re.findall(r'\w+', tl)) <= 0
                if not nprop and not istag:
                    if ('=' in line or ';' in line) and not incomment and not iscomment:
                        fis = re.findall(r'(?<=\s)\w+(?=\s*\=)', line)
                        if len(fis) <= 0:
                            fis = re.findall(r'(?<=\s)\w+(?=\s*\;)', line)
                        if len(fis) > 0:
                            nfield = fis[0]
                            if ntp not in fields:
                                fields[ntp] = {}
                            fields[ntp][nfield] = ""
                    else:
                        props = re.findall(r'(?<=\s)\w+(?=\s*\{)', line)
                        if len(props) > 0 and props[0] != ntp and not incomment and not iscomment:
                            nprop = props[0]
                            if ntp not in properties:
                                properties[ntp] = {}
                            properties[ntp][nprop] = ""

                if nprop:
                    if blockstart:
                        propb += 1
                    properties[ntp][nprop] += line + "\n"
                    if blockend:
                        propb -= 1
                        if propb == 0:
                            nprop = ""
                else:
                    if nfield:
                        if blockstart:
                            fieldb += 1
                        fields[ntp][nfield] += line + "\n"
                        if ";" in fields[ntp][nfield] and not incomment and not iscomment:
                            nfield = ""
                        if blockend:
                            fieldb -= 1
                            if fieldb == 0:
                                nfield = ""

    # for k, v in classes.items():
    #     print("class ", k)
    #     print(v)

    # for tp, fds in fields.items():
    #     for k, v in fds.items():
    #         print("field:", k, "tp:", tp)
    #         print(v)

    # for k, v in structs.items():
    #     print("struct:", k)
    #     print(v)
    #

    # for k, v in enums.items():
    #     print("enum:", k)
    #     print(v)

    # for tp, pps in properties.items():
    #     for k, v in pps.items():
    #         print("prop:", k, "tp:", tp)
    #         print(v)
    # for tp, mets in methods.items():
    #     for a, b in classes.items():
    #         print("class--------------", a)
    #     for k, v in mets.items():
    #         print("method:", k, "tp:", tp)
    #         print("---------------------------------------")
    # print("head:\n", head)
    return head, classes, structs, enums, methods, properties, fields


if __old_gitv:
    os.system("git diff %s>diff.txt" % __old_gitv)
    with open("diff.txt", 'rb') as fs:
        content, coding = decodeall(fs.read(), True)
        fits = content.split('diff --git')
        for one in fits:
            if "autofixtag.py" in one:
                continue
            fitcs = re.findall(r'(?<=a/).*[.]cs\b(?= b/)', one)
            if len(fitcs) > 0:
                path = fitcs[0]
                if not is_ignored(path):
                    if "@@ -0,0" in one:
                        print("new file ", path)
                        content, coding = read_content(path)
                        head, classes, structs, enums, methods, properties, fields = unpack(content)
                        tps = {**classes, **structs, **enums}
                        for cn, one in tps.items():
                            print(one in content)
                            content = content.replace(one, "[IFix.Interpret]\n" + one)
                        with open(path, 'w', encoding=coding) as ps:
                            ps.write(content.replace("\r\n", "\n"))
                    else:
                        os.system("git reset %s %s" % (__old_gitv, path))
                        os.system("git checkout %s" % path)
                        oldcontent, ocoding = read_content(path)
                        os.system("git reset HEAD")
                        os.system("git checkout %s" % path)
                        content, coding = read_content(path)
                        head, classes, structs, enums, methods, properties, fields = unpack(content)
                        ohead, oclasses, ostructs, oenums, omethods, oproperties, ofields = unpack(oldcontent)


                        def checkdiff(ndic, odic):
                            diffs = {}
                            newads = {}
                            for tp, fds in ndic.items():
                                for fd in fds:
                                    if tp not in odic or fd not in odic[tp]:
                                        if tp not in newads:
                                            newads[tp] = []
                                        if fd not in newads[tp]:
                                            newads[tp].append(fd)
                                    else:
                                        if ndic[tp][fd].replace("\n", "").replace("\r", "").replace(" ", "") != \
                                                odic[tp][fd].replace("\n", "").replace("\r", "").replace(" ", ""):
                                            if tp not in diffs:
                                                diffs[tp] = []
                                            if fd not in diffs[tp]:
                                                diffs[tp].append(fd)
                            return diffs, newads


                        needtag = False
                        dif, adds = checkdiff(fields, ofields)
                        for tp, diffs in dif.items():
                            for x in diffs:
                                print("=======================property not support ", tp, fields[tp][x])
                        for tp, diffs in adds.items():
                            for x in diffs:
                                print("=======================property not support ", tp, fields[tp][x])
                        dif, adds = checkdiff(properties, oproperties)
                        for tp, diffs in dif.items():
                            for x in diffs:
                                print("=======================property not support ", tp, properties[tp][x])
                        for tp, diffs in adds.items():
                            for x in diffs:
                                print("=======================property not support ", tp, properties[tp][x])
                        dif, adds = checkdiff(methods, omethods)
                        for tp, diffs in dif.items():
                            needtag = True
                            for x in diffs:
                                ma = re.findall(r"[^)]*\)", methods[tp][x])[0].replace(" ", "").replace("\r",
                                                                                                        "").replace(
                                    "\n", "")
                                if ma not in omethods[tp][x].replace(" ", "").replace("\r", "").replace("\n", ""):
                                    print("=======================not support params change ", tp, x)
                                else:
                                    if x == tp:
                                        print("=======================not support for construct ", tp, x)
                                    else:
                                        c = methods[tp][x][:len(methods[tp][x]) - 1]
                                        content = content.replace(c, "    [IFix.Patch]\n" + c)
                        for tp, diffs in adds.items():
                            needtag = True
                            for x in diffs:
                                if "override" in methods[tp][x] or tp == x:
                                    print("=======================not support for override or construct", tp, x)
                                else:
                                    c = methods[tp][x][:len(methods[tp][x]) - 1]
                                    content = content.replace(c, "    [IFix.Interpret]\n" + c)
                        tps = {**classes, **enums, **structs}
                        otps = {**oclasses, **enums, **structs}
                        for k, v in tps.items():
                            if k not in otps:
                                content = content.replace(v, "[IFix.Interpret]\n" + v)
                                needtag = True

                        if needtag:
                            with open(path, 'w', encoding=coding) as ps:
                                ps.write(content.replace("\r\n", "\n"))


else:
    print("shipped")
if os.path.exists("diff.txt"):
    os.remove("diff.txt")
