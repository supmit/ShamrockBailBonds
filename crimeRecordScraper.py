import os, sys, re, time, gzip
import urllib, urllib2, httplib
from BeautifulSoup import BeautifulSoup
from urlparse import urlparse, urlsplit
from StringIO import StringIO
import datetime, mimetools
import xlrd
import random


"""
Some utility function definitions
"""
def urlEncodeString(s):
    tmphash = {'str' : s }
    encodedStr = urllib.urlencode(tmphash)
    encodedPattern = re.compile(r"^str=(.*)$")
    encodedSearch = encodedPattern.search(encodedStr)
    encodedStr = encodedSearch.groups()[0]
    encodedStr = encodedStr.replace('.', '%2E')
    encodedStr = encodedStr.replace('-', '%2D')
    encodedStr = encodedStr.replace(',', '%2C')
    return (encodedStr)


def encode_multipart_formdata(fields):
    BOUNDARY = mimetools.choose_boundary()
    CRLF = '\r\n'
    L = []
    for (key, value) in fields.iteritems():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    content_length = str(len(body))
    return content_type, content_length, body


def getTimeStampString():
    ts = time.time()
    ts_str = int(ts).__str__()
    return (ts_str)


class NoRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl

    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302 




class JailInmateInformationBot(object):
    absUrlPattern = re.compile(r"^https?:\/\/", re.IGNORECASE)
    htmlTagPattern = re.compile(r"<[^>]+>", re.MULTILINE | re.DOTALL)
    newlinePattern = re.compile(r"\n")
    multipleWhitespacePattern = re.compile(r"\s+")
    pathEndingWithSlashPattern = re.compile(r"\/$")
    emptyStringPattern = re.compile(r"^\s*$", re.MULTILINE | re.DOTALL)

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}
    # Set DEBUG to False on prod env
    DEBUG = True


    def __init__(self, siteUrl, proxyUrlsList=[]):
        self.opener = urllib2.build_opener() # This is my normal opener....
        self.no_redirect_opener = urllib2.build_opener(urllib2.HTTPHandler(), urllib2.HTTPSHandler(), NoRedirectHandler()) # this one won't handle redirects.
        #self.debug_opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-US,en;q=0.8', 'Accept-Encoding' : 'gzip,deflate,sdch', 'Connection' : 'keep-alive', 'Host' : '' }
        self.homeDir = os.getcwd()
        self.websiteUrl = siteUrl
        self.requestUrl = self.websiteUrl
        self.baseUrl = None
        self.pageRequest = None
        self.proxyServers = proxyUrlsList
        if proxyUrlsList.__len__() > 0:
            self.requestUrl = self.__class__.selectProxyRandom(self.proxyServers)
        if self.websiteUrl:
            parsedUrl = urlparse(self.requestUrl)
            self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc
            self.httpHeaders['Host'] = parsedUrl.netloc
            # Here we just get the webpage pointed to by the website URL
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
        self.pageResponse = None
        self.requestMethod = "GET"
        self.postData = {}
        self.sessionCookies = None
        self.currentPageContent = None
        if self.websiteUrl:
            try:
                self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
            except:
                print __file__.__str__() + ": Couldn't fetch page due to limited connectivity. Please check your internet connection and try again - %s\n"%(sys.exc_info()[1].__str__())
	    	return(None)
            self.httpHeaders["Referer"] = self.requestUrl
            self.httpHeaders["Origin"] = self.baseUrl
            self.httpHeaders["Content-Type"] = 'application/x-www-form-urlencoded'
            # Initialize the account related variables...
            self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
            if not self.currentPageContent:
                print "Could not access the website content of " + self.requestUrl
            if self.proxyServers.__len__() > 0:
                self.requestUrl = self.requestUrl + "/process.php"
                self.postData = {'u' : self.websiteUrl, 'ssl' : '0', 'server' : '0', 'obfuscation' : '1'}
                formDataEncoded = urllib.urlencode(self.postData)
                self.httpHeaders['Content-Length'] = formDataEncoded.__len__()
                self.pageRequest = urllib2.Request(self.requestUrl, formDataEncoded, self.httpHeaders)
                try:
                    while True:
                        self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
                        self.sessionCookies = re.sub("\s+", "", self.sessionCookies.__str__())
                        if self.sessionCookies != "None":
                            self.httpHeaders["Cookie"] = self.sessionCookies
                        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
                        responseHeaders = self.pageResponse.info()
                        if responseHeaders.has_key('Location'):
                            self.requestUrl = responseHeaders['Location']
                            if self.httpHeaders.has_key('Content-Length'):
                                self.httpHeaders.pop('Content-Length')
                            if self.httpHeaders.has_key('Content-Type'):
                                self.httpHeaders.pop('Content-Type')
                            self.httpHeaders['Cache-Control'] = 'max-age=0'
                            if re.match(re.compile("^http://hidemyass.com/"), self.requestUrl):
                                urlParts = self.requestUrl.split("/")
                                urlParts[2] = "6." + urlParts[2]
                                self.requestUrl = "/".join(urlParts)
                            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
                        else:
                            break
                except:
                    print "Could not fetch page from %s\n: %s"%(self.requestUrl, sys.exc_info()[1].__str__())
                    return (None)
            else:
                pass


    def selectProxyRandom(cls, proxyList):
        randomNum = int(proxyList.__len__() * random.random())
        return(proxyList[randomNum])
    selectProxyRandom = classmethod(selectProxyRandom)

    """
    Cookie extractor method to get cookie values from the HTTP response objects. (class method)
    """
    def _getCookieFromResponse(cls, lastHttpResponse):
        cookies = ""
        lastResponseHeaders = lastHttpResponse.info()
        responseCookies = lastResponseHeaders.getheaders("Set-Cookie")
        pathCommaPattern = re.compile(r"path=/\s*;?", re.IGNORECASE)
        domainPattern = re.compile(r"Domain=[^;]+;?", re.IGNORECASE)
        expiresPattern = re.compile(r"Expires=[^;]+;?", re.IGNORECASE)
	deletedPattern = re.compile(r"=deleted;", re.IGNORECASE)
        if responseCookies.__len__() >= 1:
            for cookie in responseCookies:
                cookieParts = cookie.split("path=/")
                cookieParts[0] = re.sub(domainPattern, "", cookieParts[0])
                cookieParts[0] = re.sub(expiresPattern, "", cookieParts[0])
                cookieParts[0] = re.sub(pathCommaPattern, "", cookieParts[0])
		deletedSearch = deletedPattern.search(cookieParts[0])
		if deletedSearch:
		    continue
                cookies += "; " + cookieParts[0]
	    multipleWhiteSpacesPattern = re.compile(r"\s+")
	    cookies = re.sub(multipleWhiteSpacesPattern, " ", cookies)
	    multipleSemicolonsPattern = re.compile(";\s*;")
	    cookies = re.sub(multipleSemicolonsPattern, "; ", cookies)
	    if re.compile("^\s*;").search(cookies):
		cookies = re.sub(re.compile("^\s*;"), "", cookies)
            return(cookies)
	else:
	    return(None)
    
    _getCookieFromResponse = classmethod(_getCookieFromResponse)


    def _decodeGzippedContent(cls, encoded_content):
        response_stream = StringIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        return(decoded_content)

    _decodeGzippedContent = classmethod(_decodeGzippedContent)


    def getPageContent(self):
        if self.pageResponse:
            content = self.pageResponse.read()
            self.currentPageContent = content
            # Remove the line with 'DOCTYPE html PUBLIC' string. It sometimes causes BeautifulSoup to fail in parsing the html
            #self.currentPageContent = re.sub(r"<.*DOCTYPE\s+html\s+PUBLIC[^>]+>", "", content)
            return(self.currentPageContent)
        else:
            return None


    def iterateOverPages(self, outfile):
        fo = open(outfile, "w")
        pageCtr = 1
        while True:
            content = self.currentPageContent
            soup = BeautifulSoup(content)
            nextList = soup.find("li", {'class' : 'next'})
            print "Processing page #%s...\n"%pageCtr
            if nextList:
                anchor = nextList.find("a")
                self.requestUrl = anchor['href']
                inmatesInfo = self.inmatesInfo(fo)
                self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                    self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
                    pageCtr += 1
                except:
                    print "Could not fetch the next page: %s\n"%sys.exc_info()[1].__str__()
                    break
            else:
                break # Break out of the loop
        fo.close()


    def inmatesInfo(self, fo):
        inmatesInfoList = []
        # print headers
        fo.write("\"Name\", \"Address\", \"DOB\", \"Booking ID\", \"Booking Time\", \"Bonds\", \"Bond Type\", \"Bond Paid\", \"Race\", \"Sex\", \"Height\", \"Weight\", \"Eyes\", \"Case No.\", \"Court\", \"Type\"\n")
        soup = BeautifulSoup(self.currentPageContent)
        allTRs = soup.findAll("tr", {'class' : 'odd'})
        for tr in allTRs:
            name = tr.find("a").getText()
            detailsPageAnchor = tr.find("a")
            detailsPageUrl = detailsPageAnchor['href']
            bookingIdContent = tr.find("td").getText()
            bookingIdPattern = re.compile(r"Booking\s+#\s+(\d+)", re.MULTILINE | re.DOTALL)
            bookingIdSearch = bookingIdPattern.search(bookingIdContent)
            bookingId = ""
            if bookingIdSearch:
                bookingId = bookingIdSearch.groups()[0]
            allTDs = tr.findAll("td")
            tdCtr = 0
            for td in allTDs:
                if tdCtr == 1:
                    tdText = td.getText()
                    dob = re.sub("DOB:", "", tdText)
                    dob = re.sub(self.__class__.htmlTagPattern, "", dob)
                    dob = re.sub(re.compile(r"[^\d\-\s:]+", re.MULTILINE | re.DOTALL), "", dob)
                elif tdCtr == 2:
                    tdText = td.getText()
                    bookingTime = re.sub(re.compile("Booking\s+Time:", re.IGNORECASE | re.MULTILINE | re.DOTALL), "", tdText)
                    bookingTime = re.sub(self.__class__.htmlTagPattern, "", bookingTime)
                    bookingTime = re.sub(re.compile("[^\d:\-\s]+", re.MULTILINE | re.DOTALL), "", bookingTime)
                elif tdCtr == 3:
                    tdText = td.getText()
                    bonds = re.sub(self.__class__.htmlTagPattern, "", tdText)
                    bonds = re.sub(self.__class__.htmlTagPattern, "", bonds)
                    bonds = re.sub(re.compile(","), "__COMMA__", bonds) # Commas in the numerical figures are replaced with '__COMMA__' to avoid break up in CSV.
                else:
                    pass
                tdCtr += 1
            inamesInfo = {'name' : name, 'dob' : dob, 'booking_id' : bookingId, 'bonds' : bonds, 'booking_time' : bookingTime, 'sex' : '', 'weight' : '', 'case_num' : ''}
            urlParts = detailsPageUrl.split("/")
            urlParts[2] = "6." + urlParts[2]
            detailsPageUrl = "/".join(urlParts)
            self.requestUrl = detailsPageUrl
            self.pageRequest = urllib2.Request(self.requestUrl, None, self.httpHeaders)
            try:
                self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
            except:
                print "Could not fetch inmate details page for %s: %s"%(name, sys.exc_info()[1].__str__())
                continue
            soupdetails = BeautifulSoup(self.currentPageContent)
            allOddTRs = soupdetails.findAll("tr", {'class' : 'odd'})
            ctr = 0
            for tr in allOddTRs:
                if ctr == 1:
                    allTDs = tr.findAll("td")
                    tdCtr = 0
                    for td in allTDs:
                        if tdCtr == 0:
                            tdText = td.getText()
                            pat1 = re.compile(r"Race:\s*(\w+)\s*", re.MULTILINE | re.DOTALL)
                            srch1 = pat1.search(tdText)
                            if srch1:
                                inamesInfo['race'] = srch1.groups()[0]
                        elif tdCtr == 1:
                            tdText = td.getText()
                            pat2 = re.compile(r"Sex:\s*(\w+)\s*", re.MULTILINE | re.DOTALL)
                            srch2 = pat2.search(tdText)
                            if srch2:
                                inamesInfo['sex'] = srch2.groups()[0]
                        else:
                            pass
                        tdCtr += 1
                elif ctr == 2:
                    allTDs = tr.findAll("td")
                    tdCtr = 0
                    for td in allTDs:
                        if tdCtr == 0:
                            tdText = td.getText()
                            pat1 = re.compile(r"Ht\*:\s*(\d+\-?\d*)\s*", re.MULTILINE | re.DOTALL)
                            srch1 = pat1.search(tdText)
                            if srch1:
                                inamesInfo['height'] = srch1.groups()[0]
                        elif tdCtr == 1:
                            tdText = td.getText()
                            #print tdText
                            pat2 = re.compile(r"Wgt\*:\s*(\d+\.?\d*)\s*", re.MULTILINE | re.DOTALL)
                            srch2 = pat2.search(tdText)
                            if srch2:
                                inamesInfo['weight'] = srch2.groups()[0]
                        elif tdCtr == 2:
                            tdText = td.getText()
                            pat3 = re.compile(r"Eyes\*:\s*(\w+)\s*", re.MULTILINE | re.DOTALL)
                            srch3 = pat3.search(tdText)
                            if srch3:
                                inamesInfo['eyes'] = srch3.groups()[0]
                        tdCtr += 1
                elif ctr == 3:
                    allTDs = tr.findAll("td")
                    tdCtr = 0
                    for td in allTDs:
                        if tdCtr == 1:
                            tdText = td.getText()
                            pat1 = re.compile(r"Last\s+Known\s+Address:\s*(.*)\s*", re.MULTILINE | re.DOTALL)
                            srch1 = pat1.search(tdText)
                            if srch1:
                                inamesInfo['last_known_address'] = srch1.groups()[0]
                        tdCtr += 1
                elif ctr == 5:
                    allTDs = tr.findAll("td")
                    tdCtr = 0
                    for td in allTDs:
                        if tdCtr == 2:
                            tdText = td.getText()
                            pat1 = re.compile(r"Type:\s*(\w+)\s*", re.MULTILINE | re.DOTALL)
                            srch1 = pat1.search(tdText)
                            if srch1:
                                inamesInfo['type'] = srch1.groups()[0]
                        tdCtr += 1
                elif ctr == 6:
                    allTDs = tr.findAll("td")
                    tdCtr = 0
                    for td in allTDs:
                        if tdCtr == 0:
                            tdText = td.getText()
                            pat1 = re.compile(r"Bond\s+Type:\s*(.*)\s*", re.MULTILINE | re.DOTALL)
                            srch1 = pat1.search(tdText)
                            if srch1:
                                inamesInfo['bond_type'] = srch1.groups()[0]
                        elif tdCtr == 1:
                            tdText = td.getText()
                            pat2 = re.compile(r"Bond\s+Amt:\s*([\d\.]+)\s*", re.MULTILINE | re.DOTALL)
                            srch2 = pat2.search(tdText)
                            if srch2:
                                inamesInfo['bond_amt'] = srch2.groups()[0]
                        elif tdCtr == 2:
                            tdText = td.getText()
                            pat3 = re.compile(r"Bond\s+Paid:\s*([\w\s]{0,})\s*", re.MULTILINE | re.DOTALL)
                            srch3 = pat3.search(tdText)
                            if srch3:
                                inamesInfo['bond_paid'] = srch3.groups()[0]
                        else:
                            pass
                        tdCtr += 1
                elif ctr == 7:
                    allTDs = tr.findAll("td")
                    tdCtr = 0
                    for td in allTDs:
                        if tdCtr == 0:
                            tdText = td.getText()
                            pat1 = re.compile(r"Case\s+No:\s*([\w\d]+)\s*", re.MULTILINE | re.DOTALL)
                            srch1 = pat1.search(tdText)
                            if srch1:
                                inamesInfo['case_num'] = srch1.groups()[0]
                        elif tdCtr == 1:
                            tdText = td.getText()
                            pat2 = re.compile(r"Court:\s*([\w\s]+)\s*", re.MULTILINE | re.DOTALL)
                            srch2 = pat2.search(tdText)
                            if srch2:
                                inamesInfo['court'] = srch2.groups()[0]
                        else:
                            pass
                        tdCtr += 1
                else:
                    pass
                ctr += 1
            # Following information needs to be collected: Race, Sex, Height, Weight, Eyes, Last Known Address, CaseNo, Court, Bond Type, Bond Paid, Type.
            fo.write('"' + inamesInfo['name'] + '", "' + inamesInfo['last_known_address'] + '", "' + inamesInfo['dob'] + '", "' + inamesInfo['booking_id'] + '", "' + inamesInfo['booking_time'] + '", "' + inamesInfo['bonds'] + '", "' + inamesInfo['bond_type'] + '", "' + inamesInfo['bond_paid'] + '", "' + inamesInfo['race'] + '", "' + inamesInfo['sex'] + '", "' + inamesInfo['height'] + '", "' + inamesInfo['weight'] + '", "' + inamesInfo['eyes'] + '", "' + inamesInfo['case_num'] + '", "' + inamesInfo['court'] + '", "' + inamesInfo['type'] + '"\n')
            inmatesInfoList.append(inamesInfo)
        return(inmatesInfoList)
            


if __name__ == "__main__":
    outfile = "output.csv"
    if sys.argv.__len__() > 0:
        outfile = sys.argv[1]
    jbot = JailInmateInformationBot("http://www.sheriffleefl.org/main/index.php?r=crimeActivity/inmateIndex&type=bookingsToday", ['http://hidemyass.com'])
    jbot.iterateOverPages(outfile)

