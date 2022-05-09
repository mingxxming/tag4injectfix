import os
import re
import shutil

__base_versions = {
    "v100306": 'cdb0976bcb',
}
__field_support = True
__ignores = [".*SocketAPI\.cs", ".*WebAPI\.cs", ".*data/.*", ".*/Editor/.*", ".*/ExcelDll.*", ".*SimpleJSON.*", ".*CHotDataConst.*", ".*SHotDataConst.*",
             ".*XLuaSetting.*", ".*BundleLoader\.cs", ".*OBBUtil\.cs", ".*Test/.*"]
__ignore_defines = ["UnityEditor"]
__proj_files = {
    "Assembly-CSharp.csproj": {
        "add": ["UNITY_ANDROID"],
        "remove": ["UNITY_EDITOR"]
    },
    "Assembly-CSharp-firstpass.csproj": {
        "add": ["UNITY_ANDROID"],
        "remove": ["UNITY_EDITOR"]
    },
}
__compile_dir = "./"
__out_put = "patches/"
__tags = ["[^\n]*Interpret]", "[^\n]*Patch]"]
__result = "./result.txt"

if os.path.exists(__result):
    os.remove(__result)

result = ""

__debug = {
}


def is_ignored(one):
    for x in __ignores:
        if re.match(x, one):
            return True
    return False


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

    defines = re.findall("#if(?:.|\n)*?#endif", content)
    for d in defines:
        for ond in __ignore_defines:
            tgs = re.findall("(?<=#)[^!]*%s(?:.|\n)*?(?=[^/]#)" % ond, d)
            for t in tgs:
                heads = re.findall(".*%s" % ond, t)
                for h in heads:
                    t = t.replace(h, "")
                nd = d.replace(t, "\n")
                content = content.replace(d, nd)
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
        clss = re.findall('(?<=%s)\s*\w+' % tp, line)
        if len(clss) > 0 and len(re.findall('\w+%s' % tp, line)) <= 0:
            n = clss[0].replace(" ", "")
            dic[n] = ""
            isnew = True
        if n:
            for x in line:
                if "{" == x:
                    numb += 1
                if "}" == x:
                    numb -= 1
            dic[n] += line
            if be:
                if numb == 0:
                    n = ""
            if n:
                dic[n] += '\n'
        return n, numb, isnew

    for i in range(0, len(sps)):
        line = sps[i]
        
        comments = re.findall(r"\/\*.*\*\/", line)
        for cm in comments:
            line = line.replace(cm, "")


        if not incomment:
            incomment = "/*" in line
        else:
            if "*/" in line:
                incomment = False
        iscomment = "*/" in line or len(re.findall(r'<param.*param>', line)) > 0 or "///" in line or len(
            re.findall(r"\n\s*//.*", "\n" + line)) > 0
        fline = re.findall(r"\w+\s*//", line)
        fline = fline[0] if len(fline) > 0 else line

        bsn = 0
        ben = 0
        for x in fline:
            if "{" == x:
                bsn += 1
            if "}" == x:
                ben += 1

        blockstart = bsn > ben and not incomment and not iscomment
        blockend = ben > bsn and not incomment and not iscomment

        if not incomment:
            ncls, classb, aisnew = checkcls("class", line, classb, classes, ncls, blockstart, blockend)
            nstruct, structb, bisnew = checkcls("struct", line, structb, structs, nstruct, blockstart, blockend)
            nenum, enumb, cisnew = checkcls("enum", line, enumb, enums, nenum, blockstart, blockend)
            isnew = aisnew or bisnew or cisnew
        if not ncls and not nstruct and not nenum and "}" not in line:
            head += line + "\n"
        if ncls and nenum:
            continue
        if ncls or nstruct:
            ntp = ncls if ncls else nstruct

            if not nprop and not nmethod and ";" not in line and not iscomment and not incomment and "=>" not in line:
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


__tag_func_map = {}
__tag_cls_map = {}


def add_cls_tag(clsn, tagv, tag):
    #if clsn not in __tag_cls_map:
    __tag_cls_map[clsn] = {}
    __tag_cls_map[clsn][tagv] = tag


def get_cls_tag(clsn):
    res = ""
    if clsn in __tag_cls_map:
        for k, v in __tag_cls_map[clsn].items():
            res += "#if %s \n\t%s\n#endif\n" % (k, v)
    return res


def add_func_tag(clsn, funcn, tagv, tag):
    if clsn not in __tag_func_map:
        __tag_func_map[clsn] = {}
    #if funcn not in __tag_func_map[clsn]:
    __tag_func_map[clsn][funcn] = {}
    __tag_func_map[clsn][funcn][tagv] = tag


def get_func_tag(clsn, funcn):
    res = ""
    if clsn in __tag_func_map and funcn in __tag_func_map[clsn]:
        for k, v in __tag_func_map[clsn][funcn].items():
            res += "#if %s \n\t\t%s\n#endif\n" % (k, v)
    return res


if os.path.exists("./script_temp"):
    shutil.rmtree("./script_temp")


def start_check(tagv, gitv):
    global result
    os.system("git co *.cs")
    os.system("git diff %s -- *.cs>diff.txt" % gitv)
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
                    tempp = os.path.join("./script_temp/", path + ".bak")
                    if not os.path.exists(tempp):
                        fd = tempp[:tempp.rindex("/")]
                        if not os.path.exists(fd):
                            os.makedirs(fd)
                        if not os.path.exists(path):
                            continue
                        shutil.copyfile(path, tempp)
                    tempcon, temc = read_content(tempp)
                    result += tagv + "\t" + gitv + "\tcheck path\t" + path + "\n"
                    if "@@ -0,0" in one:
                        result += tagv + "\t" + gitv + "\tnew file\t" + path + "\n"
                        print("new file ", path)
                        content, coding = read_content(path)
                        head, classes, structs, enums, methods, properties, fields = unpack(content)
                        tps = {**classes, **structs}
                        for cn, one in tps.items():
                            print(one in tempcon)
                            add_func_tag(cn, cn, tagv, "[IFix.Interpret]")
                            tempcon = tempcon.replace(one, get_func_tag(cn, cn) + one)
                        with open(tempp, 'w', encoding=temc) as ps:
                            ps.write(tempcon.replace("\r\n", "\n"))
                    else:
                        os.system("git reset %s %s" % (gitv, path))
                        os.system("git checkout %s" % path)
                        oldcontent, ocoding = read_content(path)
                        os.system("git reset HEAD")
                        os.system("git checkout %s" % path)
                        content, coding = read_content(path)
                        head, classes, structs, enums, methods, properties, fields = unpack(content)
                        ohead, oclasses, ostructs, oenums, omethods, oproperties, ofields = unpack(oldcontent)

                        for dbn in __debug:
                            if dbn in path:
                                for om in methods[dbn.replace(".cs", "")]:
                                    result += tagv + "\t" + gitv + "\t--------------------------------check new  method\t" + path + "\t" + om + "\n"
                                    if om in __debug[dbn]:
                                        result += methods[dbn.replace(".cs", "")][om] + "\n"

                        def checkdiff(ndic, odic):
                            global result
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
                            for tp, lst in diffs.items():
                                for x in lst:
                                    result += tagv + "\t" + gitv + "\tadd diff\t" + tp + "\t" + x + "\n"
                            for tp, lst in newads.items():
                                for x in lst:
                                    result += tagv + "\t" + gitv + "\tadd new\t" + tp + "\t" + x + "\n"
                            return diffs, newads

                        needtag = False
                        dif, adds = checkdiff(fields, ofields)
                        for tp, diffs in dif.items():
                            for x in diffs:
                                result += tagv + "\t" + gitv + "\tproperty not support\t" + tp + "\t" + fields[tp][
                                    x] + "\n"
                                print("=======================property not support ", tp, fields[tp][x])
                        for tp, diffs in adds.items():
                            for x in diffs:
                                if not __field_support:
                                    result += tagv + "\t" + gitv + "\tproperty not support\t" + tp + "\t" + fields[tp][
                                        x] + "\n"
                                    print("=======================property not support ", tp, fields[tp][x])
                                else:
                                    c = fields[tp][x][:len(fields[tp][x]) - 1]
                                    add_func_tag(tp, x, tagv, "[IFix.Interpret]")
                                    if c not in tempcon:
                                        result += "\nerror: %s-%s not pair with origin " % (tp, x)
                                        c = re.findall("%s[^{]*{" % (c[:c.index(x)]), c)[0]
                                    tempcon = tempcon.replace(c, get_func_tag(tp, x) + c)
                                    needtag = True

                        dif, adds = checkdiff(properties, oproperties)
                        for tp, diffs in dif.items():
                            for x in diffs:
                                result += tagv + "\t" + gitv + "\tproperty not support\t" + tp + "\t" + fields[tp][
                                    x] + "\n"
                                print("=======================property not support ", tp, properties[tp][x])
                        for tp, diffs in adds.items():
                            for x in diffs:
                                if not __field_support:
                                    result += tagv + "\t" + gitv + "\tproperty not support\t" + tp + "\t" + fields[tp][
                                        x] + "\n"
                                    print("=======================property not support ", tp, properties[tp][x])
                                else:
                                    c = properties[tp][x][:len(properties[tp][x]) - 1]
                                    add_func_tag(tp, x, tagv, "[IFix.Interpret]")
                                    if c not in tempcon:
                                        result += "\nerror: %s-%s not pair with origin " % (tp, x)
                                        c = re.findall("%s[^{]*{" % (c[:c.index(x)]), c)[0]
                                    tempcon = tempcon.replace(c, get_func_tag(tp, x) + c)
                                    needtag = True

                        dif, adds = checkdiff(methods, omethods)
                        for tp, diffs in dif.items():
                            needtag = True
                            for x in diffs:
                                ma = re.findall(r"[^)]*\)", methods[tp][x])[0].replace(" ", "").replace("\r",
                                                                                                        "").replace(
                                    "\n", "")
                                if ma not in omethods[tp][x].replace(" ", "").replace("\r", "").replace("\n", ""):
                                    result += tagv + "\t" + gitv + "\tnot support params change\t" + tp + "\t" + x + "\n"
                                    print("=======================not support params change ", tp, x)
                                else:
                                    if x == tp:
                                        result += tagv + "\t" + gitv + "\tnot support for construct\t" + tp + "\t" + x + "\n"
                                        print("=======================not support for construct ", tp, x)
                                    else:
                                        c = methods[tp][x][:len(methods[tp][x]) - 1]
                                        add_func_tag(tp, x, tagv, "[IFix.Patch]")
                                        if c not in tempcon:
                                            result += "\nerror: %s-%s not pair with origin " % (tp, x)
                                            c = re.findall("%s[^{]*{" % (c[:c.index(x)]), c)[0]
                                        tempcon = tempcon.replace(c, get_func_tag(tp, x) + c)
                        for tp, diffs in adds.items():
                            needtag = True
                            for x in diffs:
                                if "override" in methods[tp][x] or tp == x:
                                    result += tagv + "\t" + gitv + "\tnot support for override or construct\t" + tp + "\t" + x + "\n"
                                    print("=======================not support for override or construct", tp, x)
                                else:
                                    c = methods[tp][x][:len(methods[tp][x]) - 1]
                                    add_func_tag(tp, x, tagv, "[IFix.Interpret]")
                                    if c not in tempcon:
                                        result += "\nerror: %s-%s not pair with origin " % (tp, x)
                                        c = re.findall("%s[^{]*{" % (c[:c.index(x)]), c)[0]
                                    tempcon = tempcon.replace(c, get_func_tag(tp, x) + c)
                        tps = {**classes, **enums, **structs}
                        otps = {**oclasses, **enums, **structs}
                        for k, v in tps.items():
                            if k not in otps:
                                add_cls_tag(k, tagv, "[IFix.Interpret]")
                                tempcon = tempcon.replace(v, get_cls_tag(k) + v)
                                needtag = True

                        if needtag:
                            with open(tempp, 'w', encoding=temc) as ps:
                                ps.write(tempcon.replace("\r\n", "\n"))
                else:
                    result += tagv + "\t" + gitv + "\tignore\t" + path + "\n"


for k, v in __base_versions.items():
    start_check(k, v)
if os.path.exists("diff.txt"):
    os.remove("diff.txt")
for rt, dir, files in os.walk("./script_temp"):
    for fn in files:
        np = os.path.join(rt, fn)
        dp = np.replace("script_temp", ".").replace(".bak", "")
        shutil.copyfile(np, dp)
shutil.rmtree("./script_temp")
os.chdir(__compile_dir)
if not os.path.exists(__out_put):
    os.mkdir(__out_put)

__temp_output = "_temp_out_put/"
if os.path.exists(__temp_output):
    shutil.rmtree(__temp_output)
os.mkdir(__temp_output)

for prj, conf in __proj_files.items():
    for tagv in __base_versions:
        content = ""
        with open(prj, "r", encoding="utf-8") as fs:
            content = fs.read()
        abns = re.findall(r"<AssemblyName>.*</AssemblyName>", content)
        filen = re.findall(r"(?<=<AssemblyName>).*(?=</AssemblyName>)", content)[0] + "_" + tagv
        for one in abns:
            content = content.replace(one, "<AssemblyName>%s</AssemblyName>" % filen)
        defines = re.findall(r"(?<=<DefineConstants>)(?:.|\n)*?(?=</DefineConstants>)", content)
        for one in defines:
            nd = one
            for a in conf["remove"]:
                nd = nd.replace(a, "")
            for a in conf["add"]:
                nd = a + ";" + nd
            nd = nd.replace(";;", ";")
            content = content.replace(one, tagv + ";" + nd)
        outputs = re.findall(r"<OutputPath>.*</OutputPath>", content)
        for one in outputs:
            content = content.replace(one, "<OutputPath>%s</OutputPath>" % __temp_output)
        with open("tempx.csproj", "w", encoding="utf-8") as fs:
            fs.write(content)
        os.system("msbuild tempx.csproj /t:Rebuild")
        shutil.copyfile(os.path.join(__temp_output, filen + ".dll"), os.path.join(__out_put, filen + ".dll"))
if os.path.exists(__temp_output):
    shutil.rmtree(__temp_output)
os.remove("tempx.csproj")
os.system("git co *.cs")
with open(__result, "w") as fs:
    fs.write(result)
