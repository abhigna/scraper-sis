#!/usr/bin/env python
# Author : Abhigna N
# Copyright (c) 2011, Abhigna N
# http://www.opensource.org/licenses/bsd-license.php
# Version 0.2
# Tool which generates a simple html report file



import re,urllib2,threading

STDOUT = False

#utility funtions
def filterl(pat,lst,rep=''):
		return map( lambda x : re.sub(pat,rep,x) ,  lst)

import string
def trans(s):
	return s.translate(string.maketrans('@','/'))

def parse_file(fl):
        dat = open(fl).readlines()
        tmp = { }
        for i in dat:
                d = i.split(':')
                if len(d) > 1:
                        tmp[d[0].strip()]=d[1].strip()
        return tmp

def gen_table(th,ar,rowa,rowb,caption=None,date=None,changed=False):
                       
	res =["<table>"]
        dstr = ""
        if changed and date:
                dstr="<p class='small'>Changed since %s</p>" % date 
        elif date:              
                dstr="<p class='small'>No change since %s</p>" % date 
     
	if caption != None :
              res.append("<caption>"+ caption + dstr +"</caption>")
       
		
	if th:
		res.append("<thead>")
		for i in th:
                        if len(i) > 0:
                                res.append("<th>"+i+"</th>")
		res.append("</thead>")
	c = 0
	row = rowa
	n = len(th)

	while c < len(ar):
                
                res.append("<tr class=\""+row+"\">")
                for i in th:
                        if len(i) == 0:
                                 c = c + 1
                                 continue
                        try :
                           res.append("<td>"+ar[c]+"</td>")
                        except IndexError : 
                                pass
                        c = c + 1

                res.append("</tr>")	
		if row == rowa:
			row = rowb
		else:
			row = rowa
		
                

	res.append("</table>")
	return "\n".join(res)


#Pages definition

def login(details):
        url = 'http://202.122.21.12:8102/servlet/SIS'
        data ='txtModule=login&txtHandler=loginHandler&txtAction=login&txtSubAction=Submit&txtUserName=%(username)s&txtPassword=%(password)s&Submit=Submit'
        req = urllib2.Request(url,data % details)
       	resp = urllib2.urlopen(req)
        rdata = resp.read()
        err_pat = re.compile(r'Invalid')
        status = re.search(err_pat,rdata)
        if status :
                print 'Invalid ID or Password'
                raise SystemExit
        return resp.headers.get('Set-Cookie')
        
        
       
def logout(cookie):
        url = 'http://202.122.21.12:8102/servlet/com.manvish.common.RoutingServlet?txtModule=login&txtHandler=loginHandler&txtAction=login&txtSubAction=logout&mainTaskCode=115&txtLogins=0'
        rql = urllib2.Request(url)
        rql.add_header('Cookie',cookie)
        rsl = urllib2.urlopen(rql)
        rsl.read()


class Page(object):
        changed = None
        ltime = None
        data = None 
        name = None
        url = None
        pgs = None
        def process(self,pg,rqh):
                pass
        def report(self):
                pass
        


class AttendancePage(Page):
        url = 'http://202.122.21.12:8102/servlet/com.manvish.common.RoutingServlet?txtModule=tasksHandler&txtHandler=acdStdAttViewHndlr&txtAction=ListPage&txtSubAction=ViewList'

        name = 'Attendance'
        pat = re.compile(r'InnerTableContent\">(.+?)</td>',re.MULTILINE | re.DOTALL)
        

        def process(self,pg,rqh):
                self.data =  [ i.group(1).strip() for i in re.finditer(self.pat,pg) ]
        
        def report(self):
                return gen_table(['Slno.','Subject name','Classes Conducted','Classes Attended','Percent'],\
                                self.data,"row-a","row-b",caption="Attendance",date=self.ltime,changed=self.changed)

class TimeTablePage(Page):
        url = 'http://202.122.21.12:8102/servlet/com.manvish.common.RoutingServlet?txtModule=academic&txtHandler=academicTimeTableStudentViewHandler&txtAction=ListPage&txtSubAction=View&txtType=N' 
        name = 'Timetable'
        data = None 
        f0 = re.compile(r"<td width=(.+?)</td>",re.DOTALL| re.MULTILINE ) 
	f1 = re.compile(r"<.+?>")
	f2 = re.compile(r"\s+")
	f3 = re.compile(r".+?>")
     
        def process(self,pg,rqh):
                lst = [ i.group(1) for i in re.finditer(self.f0,pg) ]
                self.data = filterl(self.f3, filterl ( self.f2 , filterl( self.f1 , lst[10:-4] ),' ') )
        
        def report(self):
                return gen_table(['Time',' ','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday',''],\
                                self.data,"row-a","row-b",caption="Time Table",date=self.ltime,changed=self.changed)

  
class MarksTablePage(Page):
        url = 'http://202.122.21.12:8102/servlet/com.manvish.common.RoutingServlet?txtModule=tasksHandler&txtHandler=acdStdMrkViewHndlr&txtAction=ListPage&txtSubAction=ViewList'

        name = 'MarksTable'
        
        pat=re.compile(r'InnerTableContent\">(.+?)</td>',re.MULTILINE | re.DOTALL ) 
        f1 = re.compile(r"<.+?>")
        context = {}
        pgs = None 

        parse = {  'logincode' : ( lambda pt,pg : re.search(pt,pg).group(1) , \
                                re.compile(r"name=\"loginCode\" value=\"(\d+)\">") ),

                   'studentcode' : ( lambda pt,pg : re.search(pt,pg).group(1), \
                                re.compile(r"name=\"studentCode\" value=\"(\d+)\">")  ) ,

                   'subjects' : (lambda pt,pg: [(i.group(1).strip('\''),i.group(2).replace(' ','+').strip('\''))  for i in re.finditer(pt,pg) ], 
                                re.compile(r"javascript:showDetail\(('\d+'),('.+')\)") )
         }
              
        
        def process(self,pg,rqh):
             self.data = filterl(self.f1,[ i.group(1).strip() for i in re.finditer(self.pat,pg) ]) 

             for i in self.parse:
                self.context[i] = self.parse[i][0](self.parse[i][1],pg) 

             self.pgs = [] 
             for i in self.context['subjects']:
                   sc = i[0]
                   sn = i[1]
                   sp = SubjectPage( sc , sn , self.context['logincode'], self.context['studentcode'], sn.replace('+','_') )        
                   self.pgs.append(sp)     
                   #rqh.pgs.append(sp)

             rqh.fetch_more(self.pgs)
             
             
        def report(self):
                rep = []
                i = 0
                if not self.pgs:
                        return self.report_old()

                for j in self.pgs:
                        s = filter(lambda x : x!='Obtained' , j.data)
                        #print s,len(s)
                        if len(s) < 6 :
                                # for some subjects
                                s =  [ '-' ] * (6 - len(s)) + s 
                        row = self.data[i:i+5]+s
                        rep.extend(row)
                        i = i + 5

                return gen_table(['Slno','Subject Name','Subject Code','','','T1','T2','T3','Test Avg','Assignment','Avg' ]\
                                ,map(trans,rep),"row-a","row-b",caption=self.name,date=self.ltime,changed=self.changed)

                        
                        
        def report_old(self):
                return gen_table(['Slno','Subject Name','Subject Code','Test Avg.','Assignment Average'],map(trans,self.data),"row-a","row-b",caption=self.name,date=self.ltime)
                
        


class SubjectPage(Page):
        url ='http://202.122.21.12:8102/servlet/com.manvish.common.RoutingServlet?txtModule=academic&txtHandler=acdStdMrkViewHndlr&txtAction=ListPage&txtSubAction=View&hidSbjCode=%(sbjcode)s&hidSbjName=%(sbjname)s&loginCode=%(logincode)s&studentCode=%(studentcode)s'
        data = None 
        pat = re.compile(r'InnerTableContent".*?>(.+?)</td>')
        name = None

        def __init__(self,subjectcode,subjectname,logincode,studentcode,name):
                self.data = { 'sbjcode' :subjectcode ,'sbjname' :subjectname , 'logincode' : logincode , \
                                'studentcode' : studentcode }
                #print self.data
                self.name = name
                #self.url = self.url % self.data

        def get_url(self):
                return self.url % self.data

        def process(self,pg,rqh):
                self.data = [  i.group(1) for i in re.finditer(self.pat,pg) ]
                
        

        def report(self):
               return ''
               s = filter(lambda x : x!='Obtained' , self.data)
               return gen_table(['T1','T2','T3','Test Avg','Assignment','Avg' ],\
                               map(trans,s),len(s),"row-a","row-b",caption=self.name,date=self.ltime,changed=self.changed)


class RequestHandler:
        pgs = None
        result = {}
        threads = None 
        cookie = None 
 
        def fetch_all_par(self):
                self.threads = [ threading.Thread(target=self.read_pgs , args=(pg,self.cookie)) for pg in self.pgs ]
                for t in self.threads:
                        t.start()
                for t in self.threads:
                        t.join()

        def fetch_more(self,pgs):
        
                ethreads = [ threading.Thread(target=self.read_pgs ,\
                         args=( pg , self.cookie, pg.get_url() ) ) for pg in pgs ] 
                
                for t in ethreads:
                        t.start()
                for t in ethreads:
                        t.join()

        def read_pgs(self,pg,cookie,url = None):
                #if data :
                #        req = urllib2.Request(pg.url,data)
                #else:
                if not url :
                        url = pg.url
                
                req = urllib2.Request(url)
                req.add_header('Cookie',cookie)
                try:
                        pg.process(urllib2.urlopen(req).read(),self)
                except:
                        pass
                if not STDOUT:
                        print "Page received",pg.name
                
        def fetch_all_seq(self):
                for pg in pgs:
                        self.read_pgs(pg,cookie)

import sqlite3,time
import datetime
class DB:
        table = None
        conn = None
        loc = None
        cur = None 
        data = None
        ltime = None 
        
        def __init__(self,loc,table="sis_table"):
                self.loc = loc
                self.table = table
                self.data = {}
                if not os.path.isfile(loc):
                        self.create_table()
        def open(self):
                self.conn = sqlite3.connect(self.loc)
                self.conn.text_factory = str 
                self.conn.row_factory = sqlite3.Row
                self.cur = self.conn.cursor()
                
        def close(self):
                self.conn.commit()
                self.cur.close()

        def create_table(self):
                self.open()
                self.cur.execute('''create table sis_table 
                                (time REAL,name text,data text) ''')
                self.close()
        def join(self,data):
                return '|'.join(data)
                
        def insert(self,pgs):
                ctime = time.time()
                for i in pgs:
                        self.cur.execute('insert into '+self.table+' values ( ? , ? , ? )'\
                                                , ( ctime , i.name , self.join(i.data) ) )
        def get_last(self):
                self.cur.execute('select * from '+self.table+' order by time desc')

                row = self.cur.fetchone()

                if row:
                        self.data[row['name']] = row['data']
                        ltime = row['time']
                        self.ltime = ltime
               
                for i in self.cur:
                        if ltime != i['time']:
                                break                                         
                        self.data[i['name']] = i['data']

               

        def compare(self,pgs):
                if self.ltime:
                        ltime = datetime.datetime.fromtimestamp(float(self.ltime)).ctime()

                for i in pgs:
                        if i.name not in self.data:
                                continue
                        i.ltime = ltime                                
                        if self.data[i.name] != self.join(i.data) :
                                i.changed = True
                        else:
                                i.changed = False

                        


                
   
class SIS:
        rqh = None
        details = None
        
        def __init__(self,rqh,details):
                self.rqh = rqh
                self.details=details

        def get_all_plain(self):
                if not STDOUT:
                        print "logging in..."
                try :
                        cookie = login(self.details)
                        if not STDOUT :
                                 print "Cookie " ,cookie
                        try :
                            self.rqh.pgs = [AttendancePage(),MarksTablePage(),TimeTablePage()]
                            self.rqh.cookie = cookie
                            self.rqh.fetch_all_par()
                           
                        finally:
                            logout(cookie)
                except urllib2.URLError as e:
                        print "ERROR " , e.reason
                        raise SystemExit

        def get_all(self):
                if not STDOUT:
                        print "logging in..."
                try :
                        cookie = login(self.details)
                        if not STDOUT :
                                 print "Cookie " ,cookie
                        try :
                            self.rqh.pgs = [AttendancePage(),MarksTablePage(),TimeTablePage()]
                            self.rqh.cookie = cookie
                            self.rqh.fetch_all_par()
                           
                        finally:
                            logout(cookie)
                except urllib2.URLError as e:
                        print "ERROR " , e.reason
                        raise SystemExit
                
                db = DB('sis')
                db.open()
                db.get_last()
                lst = []
                for i in self.rqh.pgs:
                         lst.append(i)
                         if i.pgs:
                              lst.extend(i.pgs)
                                
                db.compare(lst)
                db.insert(lst)
                db.close()
        
       

#Report generation

def generate_report(sis):
	beg="""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html lang="en-US" xml:lang="en-US" xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Report </title>
<style type="text/css">

table
{
font-family:Verdana, sans-serif;;
font-size:12px;
line-height: 20.58px;
margin:0 auto;
border-collapse:collapse;
background-color:#FFF;
color:#333;
margin-top:10px;
}

th,td
{
border: 1px solid #AAA;
/*border-width: 1px 0px;*/
text-align:center;

padding:4px;
}
th {
font-size:11px;
font-weight:bold;
}
tr.row-b{
background-color:#EEE;
}
caption {
font-family:Georgia;
font-size:22px;
padding:5px;
}
.small {
font-family:Verdana;
font-size:10px;
padding:0px;
}
</style>
</head>
<body>
"""
       
	end="</body>\n</html>"
        lst = [beg]

	for i in sis.rqh.pgs:
        	lst.append(i.report())

	lst.append(end)
	return '\n'.join(lst)

       
                
if __name__ == '__main__':

        #Commandline options parsing

        from optparse import OptionParser
        import os,optparse

        def check_file(option, opt_str, value, parser):
                
                if not os.path.exists(value):
                         raise optparse.OptionValueError("%s doesnt seem to exist." % value )
                setattr(parser.values, option.dest, value)

        def check_loc(option, opt_str, value, parser):
                
                if not os.path.exists(os.path.dirname(value)) or os.path.isdir(value):
                         raise optparse.OptionValueError("%s is an invalid location" % value )
                setattr(parser.values, option.dest, value)


        parser = OptionParser(usage="%prog -f FILE -p FILE",version="%prog 0.2a",description="Generate a report file using sis.Run without arguments for prompt mode.")

        parser.add_option('-r','--report',dest='filename',
                        action="callback",callback=check_loc,type="string",
                            help='write report to FILE',metavar='FILE')

        parser.add_option("-o", "--output",
                  action="store_true", dest="output", default=False,
                  help="write the report to stdout")


        group = optparse.OptionGroup(parser, "Userdetails file",
                    "Format of file , the userdetails seperated by ':' on different lines "
                     )
        group.add_option('-u','--userdetails',dest='userfile',
                                action="callback",callback=check_file,type="string",
                                help='file containing userdetails',metavar='FILE')

        parser.add_option_group(group)

     

        (options, args) = parser.parse_args()
        det = {}
        loc = ''
        import getpass
        if options.output:
                import sys
                STDOUT = options.output
                try:
                   
                   det['username'] = raw_input('Username : ')
                   det['password'] = getpass.getpass('Password : ')
                   
                   sis = SIS(RequestHandler(),det)
                   sis.get_all_plain()
                   print generate_report(sis)
                    
                except IndexError:
                        parser.error("You need to enter username and password")
                except EOFError:
                        parser.error("EOF Error")
                finally:
                        raise SystemExit
                
               
       
        for i in options.__dict__:
                if not options.__dict__[i]:
                        while not os.path.exists(os.path.dirname(loc)) or os.path.isdir(loc):
                                print "Enter the required details"
                                try:
                                        det['username'] = raw_input('Username : ')
                                        det['password'] = getpass.getpass('Password : ')
                                        loc = raw_input('Location : ')
                                except EOFError:
                                        parser.error("EOF Error")
                        break
                        
        if not det:                
                det = parse_file(options.userfile)
                loc = options.filename
                            
        sis = SIS(RequestHandler(),det)
        sis.get_all()
        open(loc,'w').write(generate_report(sis))


