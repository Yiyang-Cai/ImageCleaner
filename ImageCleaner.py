#! python2
import sys
import re
import smtplib
import requests
import csv
import os
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime,timedelta

#as enum,sperate the env to clean staging or production
class Env:
    Stg="staging"
    Prd="production"

#as enum,to define the image types
class ImageType:
    template="template"
    official="official"

#to record some configure informations such as url,mail and so on.
class ConfigValue:
    Server="mail-relay.autodesk.com"
    From="itools@autodesk.com"
    To="yiyang.cai@autodesk.com"
    StgUrl="http://itools_mms_stg.ecs.ads.autodesk.com"
    PrdUrl="http://itools_mms.ecs.ads.autodesk.com"
    ArtFactory="https://art-bobcat.autodesk.com/artifactory/team-dlstools-generic/test/test.txt"

#class to send mails    
class MailUtil:
    @staticmethod
    def SendMail(from_addr,to_addr,subject,content):
        msg=MIMEText('<html><p>{0}</p></html>'.format(content),'html',"utf-8")
        msg["Subject"]=subject
        server=smtplib.SMTP(ConfigValue.Server)
        server.sendmail(from_addr,to_addr,msg.as_string())
        server.quit()
        pass
    
#to store image information
class ImageInfo:
    def __init__(self,jsonData=None):
        if(jsonData!=None):
            self.ParseJsonToImage(jsonData)
        else:
            self.id=0
            self.name=None
            self.imagetype=None
            self.provider_id=None
            self.createdate=datetime.min

    def ParseJsonToImage(self,jsonData):
        # If iamge information is invalid, its id will be assumed to be 0,
        # and don't do anything for it.
        if(not jsonData.has_key('tags') or not jsonData['tags'].has_key('type') \
                or not jsonData.has_key('createdate') \
                or not datetime.strptime(jsonData["createdate"][:-5],"%Y-%m-%dT%H:%M:%S")):
            self.id=0
            print 'Image (id = {0}) information is invalid'.format(jsonData["id"])
            return

        self.id=jsonData["id"]
        self.name=jsonData["name"]
        self.provider_id=jsonData["provider_id"]
        self.imagetype=str(jsonData["tags"]["type"])
        self.createdate=datetime.strptime(jsonData["createdate"][:-5],"%Y-%m-%dT%H:%M:%S")

#to call web api
class HttpUtil:
    
    @staticmethod
    def GetImagesInfo(url):
        auth=HttpUtil.GetAuthFromServer(url)
        if(not auth):
            print 'HTTP Error : Token Not Found.'
            return False

        response = requests.get(url = url + "/images",\
            headers = {"ACCEPT" : "application/json", "Authorization" : auth})

        if(response.status_code != 200):
            print "HTTP Error : Images Info Not Found."
            return False
        imageInfoList = [ImageInfo(item) for item in response.json()]
        return imageInfoList

    @staticmethod
    def GetAuthFromServer(url):
        response = requests.post(url = url+"/user_token",\
            data = '{\"auth\":{\"username\":\"' + os.environ.get('VIRTUAL_MANAGER_USER_NAME') \
		    +'\",\"password\":\"' + os.environ.get('VIRTUAL_MANAGER_PASS_WORD')+'\"}}', \
            headers = {"Content-Type" : "application/json", "charset" : "utf-8"})  
        if (response.status_code == 201):
            return response.json()['token']
        else:
            return False
      
    @staticmethod
    def DeleteImageByID(url, images_id):
        auth=HttpUtil.GetAuthFromServer(url)
        if(not auth):
            print 'HTTP Error : Token Not Found.'
            return False
        response = requests.delete(url=url+'/images/'+str(images_id),headers = {"Authorization" : auth})
        return response.status_code

#the cleaner to excute cleaning
class Cleaner:
    def __init__(self,env):
        self.env=env
        self.serverHost=""
        self.TransferEnv(env)
        
    def TransferEnv(self,env):
        self.env=env
        if(env==Env.Stg):
            self.serverHost=ConfigValue.StgUrl
        elif(env==Env.Prd):
            self.serverHost=ConfigValue.PrdUrl

    def GetImageBranchByName(self,imageName):
        branch=""
        m=re.compile(r"(?i)^[^_]+_[^_]+_([^_]+)_.*?WIN.*?").match(imageName)
        if(m):
            branch=str(m.groups()[0])
        else:
            branch="main"

        return branch

    def SkipLastBuildForEveryRelease(self,lstImages):
        lastBuildDict=dict()
        specialList=list()
        lstPatternStrings=list()
        lstResult=list()
        bmatch=False
        
        for img in lstImages:
            m=re.compile(r"(?i)^M(\d*)_(\d*)[^_]*_.*?WIN.*?").match(img.name)
            if(m):
                iRelease=str(m.groups()[0])+"_"+self.GetImageBranchByName(img.name)
                iBuild=int(m.groups()[1])
                if(lastBuildDict.has_key(iRelease) and lastBuildDict[iRelease]>=iBuild):
                    pass
                else:
                    lastBuildDict[iRelease]=iBuild
            else:
                #except the types that 'M<release>_<build>_<branch>' and 'M<release>_<build>'
                specialList.append(img)
        

        for key in lastBuildDict.keys():
            arr=key.split("_")
            if(arr[1]=="main"):
                lstPatternStrings.append(r"(?i)^M{0}_{1}_.*?WIN.*?".format(arr[0],str(lastBuildDict[key])))
            else:
                lstPatternStrings.append(r"(?i)^M{0}_{1}[^_]*_{2}_WIN.*?".format(arr[0],str(lastBuildDict[key]),arr[1]))

        for img in lstImages:
            for patt in lstPatternStrings:
                if(re.match(patt,img.name)):
                    bmatch=True
                    break
            if(not bmatch and img not in specialList):
                lstResult.append(img)
            bmatch=False

        return lstResult
    
    def CreateCsv(self,cleanlist=[]):
        with open("ImagesClean.csv","wb") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["image_id","image_name","create_date"])
            for item in cleanlist:
                writer.writerow(item)   

    def DeleteList(self):
        imagesInfo=None
        curr=datetime.now()
        oneMonthAgo=curr-timedelta(days=25)
        deleteList=list()
        officialList=list()

        imagesInfo=HttpUtil.GetImagesInfo(self.serverHost)
        if(not imagesInfo):
            print "Get images from server is failed!"
            return None

        for img in imagesInfo:
            if(img.id<9000 or str.lower(img.imagetype)==ImageType.template):
                pass
            elif(str.lower(img.imagetype)==ImageType.official):
                officialList.append(img)
            elif(img.createdate<=oneMonthAgo):
                deleteList.append(img)

        officialList=self.SkipLastBuildForEveryRelease(officialList)

        for image in officialList:
            if(image.createdate<=oneMonthAgo):
                deleteList.append(image)

        for dup in imagesInfo:
                if('name' not in dir(dup)):
                    continue
                else:
                    for i in range(0,len(imagesInfo)):
                        if('name' not in dir(imagesInfo[i])):
                            continue
                        elif(dup.name==imagesInfo[i].name and dup.provider_id==imagesInfo[i].provider_id and dup.id > imagesInfo[i].id):
                            deleteList.append(dup)        

        return deleteList

    def ExecuteCleaning(self):
        print "Get {0} images information from server......".format(self.env)
        csvlist=[]
        deleteList=self.DeleteList()
        if(deleteList!=None and len(deleteList)>0):
            for image in deleteList:
                csvlist.append([image.id,image.name,image.createdate.strftime("%Y-%m-%d %H:%M:%S")])
            self.CreateCsv(cleanlist=csvlist)
    
    def ExecuteDelete(self):
        content=''
        if os.path.isfile('ImagesClean.csv'):
            with open('ImagesClean.csv','r') as csvfile:
                csv_reader = csv.reader(csvfile)
                content += ("The templates below miss the options to preserve:"+"<br/><br/>")
                for image in csv_reader:
                    if image[0]!='image_id':
                        statuscode = HttpUtil.DeleteImageByID(self.serverHost,images_id=image[0])
                        content += ("&nbsp;&nbsp;&nbsp;&nbsp;"+str(image[0])+"&nbsp;&nbsp;&nbsp;&nbsp;"+str(image[1])+\
                        "&nbsp;&nbsp;&nbsp;&nbsp;"+str(image[2])+"&nbsp;&nbsp;&nbsp;&nbsp;"+str(statuscode)+"<br/>")
                MailUtil.SendMail(ConfigValue.From,ConfigValue.To,"Templates Auto Cleaner for "+self.env,content)
                print'Successful, will send mail soon'
        else:
            print "Do not have images to delete, please provide the input csvfile"
                    

if __name__=="__main__": #pragma no cover
    pass
    if(sys.argv[1]!=Env.Stg and sys.argv[1]!=Env.Prd):
        print "Cleaner needs 1 image environment, and must be: staging or production."
    elif(len(sys.argv)==3):
        if(sys.argv[2] == 'delete'):
            cleaner=Cleaner(sys.argv[1])
            cleaner.ExecuteDelete()
        else:
            print'If your are sure to cleaning image, please input: delete.'
    else:
        print "Start Cleaner......"
        cleaner=Cleaner(sys.argv[1])
        cleaner.ExecuteCleaning()
