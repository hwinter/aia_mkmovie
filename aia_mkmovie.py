__version__ = "0.0.1 (2017/07/24)"
__authors__ = ['Jakub Prchlik <jakub.prchlik@cfa.harvard.edu>']
__email__   = "jakub.prchlik@cfa.harvard.edu"


import matplotlib
#fixes multiprocess issue
matplotlib.use('agg')
import sys

try:
    import sunpy.map
    from sunpy.cm import cm
except ImportError:
    sys.stdout.write(sys.stderr,"sunpy not installed, use pip install sunpy --upgrade")

from make_movie import create_movie

from matplotlib.transforms import Bbox
import matplotlib.dates as mdates
import subprocess
import glob
import os
import stat
import numpy as np
from datetime import date,datetime
from datetime import timedelta as dt
from multiprocessing import Pool
import matplotlib.pyplot as plt
import grab_goes_xray_flux as ggxf
from mpl_toolkits.axes_grid.inset_locator import inset_axes
from astropy.io import ascii
from astropy.table import vstack,Table,join

from SMEARpy import Scream

#import hv download (probably wont do)
####def get_file(ind):
#####Source ID 11 is AIA 193
#####    fils = ind.replace(':','_').replace('/','_').replace(' ','_')+'_AIA_193.jp2'
####    meta = hv.get_closest_image(ind,sourceId=11)
####    date = meta['date'].strftime('%Y_%m_%d__%H_%M_%S')
####    mils = float(meta['date'].strftime('%f'))/1000.
####    fstr = date+'_*__SDO_AIA_AIA_193.jp2'.format(mils).replace(' ','0')
#####    test = os.path.isfile(sdir+'/raw/'+fstr)
####    test = glob.glob(sdir+'/raw/'+fstr)
####    if len(test) == 0:
#####        filep = hv.download_png(ind,0.3,"[11,1,100]",directory=sdir+'/raw',x0=0,y0=0,width=int(rv*8192),height=8192,watermark=False)#,y1=-1200,y2=1200,x1=-1900,x2=1900)
####        filep = hv.download_jp2(ind,sourceId="11",directory=sdir+'/raw',clobber=True)#,y1=-1200,y2=1200,x1=-1900,x2=1900)
####




class aia_mkimage:

    def __init__(self,dayarray,sday=False,eday=False,w0=1900.,h0=1200.,dpi=100.,sc=1.,goes=False,goesday=False,ace=False,aceadat=False,single=True,panel=False,color3=False,time_stamp=True,odir='working/'):

        #check format of input day array
        if isinstance(dayarray,list):
            self.dayarray = dayarray
            if len(dayarray) == 3: color3 = True #automatically assume rgb creation if 3 
            elif len(dayarray) == 1: color3 = False #force color 3 to be false if length 1 array
            else:
                sys.stdout.write('dayarray must be length 1 or 3')
                sys.exit(1)
        #if just a string turn the file string into a list
        elif isinstance(dayarray,str):
            self.dayarray = [dayarray]
        else:
            sys.stdout.write('dayarray must be a list or string')
            sys.exit(1)

        #check if ace flag is set
        if isinstance(ace,bool):  
            self.ace = ace
            if self.ace: goes = True #is ace is set goes must also be set
        else:
            sys.stdout.write('ace must be a boolean')
            sys.exit(1)

        #check if goes flag is set
        if isinstance(goes,bool): 
            self.goes = goes
        else:
            sys.stdout.write('goes must be a boolean')
            sys.exit(1)

        #check if timestamp flag is set (Default = True)
        if isinstance(time_stamp,bool): 
            self.timestamp = goes
        else:
            sys.stdout.write('timestamp must be a boolean')
            sys.exit(1)

        #check output directory
        if isinstance(odir,str):
            self.odir = odir
        else:
            sys.stdout.write('odir must be a string')
            sys.exit(1)
 
        #format and create output directory
        if self.odir[-1] != '/': self.odir=self.odir+'/'
        if not os.path.isdir(self.odir): os.mkdir(self.odir)
     

        #check format of acedat Table if it exits 
        if isinstance(aceadat,Table):
            self.aceadat = aceadat
        elif aceadat == False:
            self.aceadat = [] #do not plot goes data
        else:
            sys.stdout.write('acedat must be a astropy table')

        #if goes is set you must give the plot a start and end date for plotting the goes xray flux
        if self.goes:
            #check inserted end time
            if isinstance(sday,datetime):
                self.sday = sday
            elif isinstance(sday,str):
                self.sday = datetime.strptime(sday,dfmt)
            else:
                sys.stdout.write('sday must be a datetime object or formatted string')
                sys.exit(1)

            #check inserted end time
            if isinstance(eday,datetime):
                self.eday = eday
            elif isinstance(eday,str):
                self.eday = datetime.strptime(eday,dfmt)
            else:
                sys.stdout.write('eday must be a datetime object or formatted string')
                sys.exit(1)

        #check format of goesday Table if it exits 
        if isinstance(goesday,Table):
            self.goesday = goesday
        elif goesday == False:
            self.goesday = [] #do not plot goes data
        else:
            sys.stdout.write('goesday must be a astropy table')

        #check image height
        if isinstance(h0,(int,float)):
            self.h0 = h0
        else:
            sys.stdout.write('h0 must be an integer or float')
            sys.exit(1)
         
        #check image width
        if isinstance(w0,(int,float)):
            self.w0 = w0
        else: 
            sys.stdout.write('w0 must be an integer or float')
            sys.exit(1)

 
        #check dpi
        if isinstance(dpi,(int,float)):
            self.dpi = dpi
        else: 
            sys.stdout.write('dpi must be an integer or float')
            sys.exit(1)

        #check sc
        if isinstance(sc,(int,float)):
            self.sc = sc
        else: 
            sys.stdout.write('sc must be an integer or float')
            sys.exit(1)

        #check if single wavelength flag is set
        if isinstance(single,bool):
            self.single = single
        else:
            sys.stdout.write('single must be a boolean')
            sys.exit(1)
      
        #create a panel movie
        if isinstance(panel,bool):
            self.panel = panel
        else:
            sys.stdout.write('panel must be a boolean')
            sys.exit(1)
        #create 3 color image (default = False)
        if isinstance(color3,bool):
            self.color3 = color3
        else:
            sys.stdout.write('color3 must be a boolean')
            sys.exit(1)
         
        #list of acceptable wavelengths
        self.awavs = ['0094','0131','0171','0193','0211','0304','0335','1600','1700']


        #Dictionary for vmax, vmin, and color
        self.img_scale = {'0094':[cm.sdoaia94  ,np.arcsinh(1.),np.arcsinh(150.)],
                          '0131':[cm.sdoaia131 ,np.arcsinh(1.),np.arcsinh(500.)],
                          '0171':[cm.sdoaia171 ,np.arcsinh(10.),np.arcsinh(6000.)],
                          '0193':[cm.sdoaia193 ,np.arcsinh(10.),np.arcsinh(8000.)],
                          '0211':[cm.sdoaia211 ,np.arcsinh(10.),np.arcsinh(4000.)],
                          '0304':[cm.sdoaia304 ,np.arcsinh(1.),np.arcsinh(300.)],
                          '0335':[cm.sdoaia335 ,np.arcsinh(1.),np.arcsinh(100.)],
                          '1600':[cm.sdoaia1600,np.arcsinh(20.),np.arcsinh(500.)],
                          '1700':[cm.sdoaia1700,np.arcsinh(200.),np.arcsinh(4000.)]}


    #for j,i in enumerate(dayarray):
    #reformat file to be in 1900x1200 array and contain timetext
    def format_img(self):
    
            #input fits file
            self.filep = self.dayarray
          
        	
            #check image quality
            check, img = self.qual_check()
           
            #return image wavelength
            if isinstance(img,list):
                self.wav = []
                img3d = np.zeros((img[0].data.shape[0],img[0].data.shape[1],3))
                for j,i in enumerate(img):
                    self.wav.append('{0:4.0f}'.format(i.wavelength.value).replace(' ','0'))
                    #set normalized scaling for every observation
                    ivmin = self.img_scale[self.wav[j]][1]
                    ivmax = self.img_scale[self.wav[j]][2]
                    prelim = (np.arcsinh(i.data)-ivmin)/ivmax
            
                    #replace out of bounds points
                    prelim[prelim < 0.] = 0.
                    prelim[prelim > 1.] = 1.
                    img3d[:,:,j] = prelim
                #output png file
                outfi = self.odir+'AIA_{0}_'.format(img[0].date.strftime('%Y%m%d_%H%M%S'))+'{0}_{1}_{2}.png'.format(*self.wav)
            else:
                self.wav ='{0:4.0f}'.format( img.wavelength.value).replace(' ','0')
                #use default color tables
                icmap = self.img_scale[self.wav][0]
                ivmin = self.img_scale[self.wav][1]
                ivmax = self.img_scale[self.wav][2]
                outfi = self.odir+'AIA_{0}_'.format(img.date.strftime('%Y%m%d_%H%M%S'))+'{0}.png'.format(self.wav)

            #see if output file already exists
            test = os.path.isfile(outfi)
        
        #test to see if png file already exists and passes quality tests
            if ((test == False) & (check)):
                print 'Modifying file '+outfi
                fig,ax = plt.subplots(figsize=(self.sc*float(self.w0)/float(self.dpi),self.sc*float(self.h0)/float(self.dpi)))
                fig.set_dpi(self.dpi)
                fig.subplots_adjust(left=0,bottom=0,right=1,top=1)
                if self.panel: fig.subplots_adjust(vspace=0.0001,hspace=0.0001)
                ax.set_axis_off()
        		# J. Prchlik 2016/10/06
        #Block add J. Prchlik (2016/10/06) to give physical coordinate values 
                img = sunpy.map.Map(*self.filep)

                #return extent of image
                #use the first image in the list if it is a composite image to get the image boundaries
                if isinstance(img,list):
                    maxx,minx,maxy,miny = self.img_extent(img[0])
                #else use the only image
                else:
                    maxx,minx,maxy,miny = self.img_extent(img)


                

                #set text location
                if self.w0 > self.h0:
                    txtx = -(self.w0-self.h0)
                    txty = (maxy-miny)*0.01
                elif self.w0 < self.h0:
                    txty = -(self.h0-self.w0)
                    txtx = (maxx-minx)*0.01
                if self.w0 == self.h0:
                    txtx = (maxx-minx)*0.01
                    txty = (maxy-miny)*0.01

        #plot the image in matplotlib
                #use color composite image if color3 set
                if self.color3:
                    ax.imshow(np.arcsinh(img3d),interpolation='none',origin='lower',extent=[minx,maxx,miny,maxy])
                    ax.text(minx+txtx,miny+txty,'AIA {2}/{1}/{0}'.format(*self.wav)+'- {0}Z'.format(img[0].date.strftime('%Y/%m/%d - %H:%M:%S')),color='white',fontsize=36,zorder=50,fontweight='bold')
                else:
                    ax.imshow(np.arcsinh(img.data),interpolation='none',cmap=icmap,origin='lower',vmin=ivmin,vmax=ivmax,extent=[minx,maxx,miny,maxy])
                    ax.text(minx+txtx,miny+txty,'AIA {0} - {1}Z'.format(self.wav,img.date.strftime('%Y/%m/%d - %H:%M:%S')),color='white',fontsize=36,zorder=50,fontweight='bold')
                if self.goes:
                #use the first image for goes and ace plotting
                    if isinstance(img,list): img = img[0] 
    #format string for date on xaxis
                    myFmt = mdates.DateFormatter('%m/%d')
    
    #only use goes data upto observed time
    
                    use, = np.where((self.goesdat['time_dt'] < img.date+dt(minutes=150)) & (self.goesdat['Long'] > 0.0))
                    clos,= np.where((self.goesdat['time_dt'] < img.date) & (self.goesdat['Long'] > 0.0))
                    ingoes = inset_axes(ax,width="27%",height="20%",loc=7,borderpad=-27) #hack so it is outside normal boarders
                    ingoes.set_position(Bbox([[0.525,0.51],[1.5,1.48]]))
                    ingoes.set_facecolor('black')
    #set inset plotting information to be white
                    ingoes.tick_params(axis='both',colors='white')
                    ingoes.spines['top'].set_color('white')
                    ingoes.spines['bottom'].set_color('white')
                    ingoes.spines['right'].set_color('white')
                    ingoes.spines['left'].set_color('white')
    #make grid
                    ingoes.grid(color='gray',ls='dashdot')
    
                    ingoes.xaxis.set_major_formatter(myFmt)
    
                    ingoes.set_ylim([1.E-9,1.E-2])
                    ingoes.set_xlim([self.sday,self.eday])
                    ingoes.set_ylabel('X-ray Flux (1-8$\mathrm{\AA}$) [Watts m$^{-2}$]',color='white')
                    ingoes.set_xlabel('Universal Time',color='white')
                    ingoes.plot(self.goesdat['time_dt'][use],self.goesdat['Long'][use],color='white')
                    ingoes.scatter(self.goesdat['time_dt'][clos][-1],self.goesdat['Long'][clos][-1],color='red',s=10,zorder=1000)
                    ingoes.set_yscale('log')
    #plot ace information
                if ((self.ace) & (self.goes)):
                    use, = np.where((self.aceadat['time_dt'] < img.date+dt(minutes=150)) & (self.aceadat['S_1'] == 0.0) & (self.aceadat['S_2'] == 0) & (self.aceadat['Speed'] > -1000.))
                    clos,= np.where((self.aceadat['time_dt'] < img.date) & (self.aceadat['S_1'] ==  0) & (self.aceadat['S_2'] == 0) & (self.aceadat['Speed'] > -1000))
                    
                    acetop = inset_axes(ingoes,width='100%',height='100%',loc=9,borderpad=-27)
                    acebot = inset_axes(ingoes,width='100%',height='100%',loc=8,borderpad=-27)
    
    #set inset plotting information to be white
                    acetop.tick_params(axis='both',colors='white')
                    acetop.spines['top'].set_color('white')
                    acetop.spines['bottom'].set_color('white')
                    acetop.spines['right'].set_color('white')
                    acetop.spines['left'].set_color('white')
    
    #set inset plotting information to be white
                    acebot.tick_params(axis='both',colors='white')
                    acebot.spines['top'].set_color('white')
                    acebot.spines['bottom'].set_color('white')
                    acebot.spines['right'].set_color('white')
                    acebot.spines['left'].set_color('white')
    #make grid
                    acebot.grid(color='gray',ls='dashdot')
                    acetop.grid(color='gray',ls='dashdot')
    
    
                    acetop.set_facecolor('black')
                    acebot.set_facecolor('black')
    
    
                    acetop.set_ylim([0.,50.])
                    acebot.set_ylim([200.,1000.])
    
                    acetop.set_xlim([self.sday,self.eday])
                    acebot.set_xlim([self.sday,self.eday])
    
                    acetop.set_xlabel('Universal Time',color='white')
                    acebot.set_xlabel('Universal Time',color='white')
     
                    acetop.set_ylabel('B$_\mathrm{T}$ [nT]',color='white')
                    acebot.set_ylabel('Wind Speed [km/s]',color='white')
    
                    acetop.plot(self.aceadat['time_dt'][use],self.aceadat['Bt'][use],color='white')
                    acebot.plot(self.aceadat['time_dt'][use],self.aceadat['Speed'][use],color='white')
                    
                    acetop.scatter(self.aceadat['time_dt'][clos][-1],self.aceadat['Bt'][clos][-1],color='red',s=10,zorder=1000)
                    acebot.scatter(self.aceadat['time_dt'][clos][-1],self.aceadat['Speed'][clos][-1],color='red',s=10,zorder=1000)
                    
                    acebot.xaxis.set_major_formatter(myFmt)
                    acetop.xaxis.set_major_formatter(myFmt)
    
                    
                fig.savefig(outfi,edgecolor='black',facecolor='black',dpi=self.dpi)
                plt.clf()
                plt.close()
            return
    
    
    #for j,i in enumerate(dayarray):
    def qual_check(self):
    #read JPEG2000 file into sunpymap
        img = sunpy.map.Map(*self.filep)
        check = True
    #Level0 quality flag equals 0 (0 means no issues)
        if isinstance(img,list):
            #loop over all images
            for i in img:
                #exit if check ever fails
                if check:
                    lev0 = i.meta['quallev0'] == 0
                #check level1 bitwise keywords (http://jsoc.stanford.edu/doc/keywords/AIA/AIA02840_K_AIA-SDO_FITS_Keyword_Document.pdf)
                    lev1 = np.binary_repr(i.meta['quality']) == '1000000000000000000000000000000'
                #check that both levels pass and it is not a calibration file
                    check = ((lev0) & (lev1))# & (calb)) 
                else: 
                    continue
        else:
            lev0 = img.meta['quallev0'] == 0
        #check level1 bitwise keywords (http://jsoc.stanford.edu/doc/keywords/AIA/AIA02840_K_AIA-SDO_FITS_Keyword_Document.pdf)
            lev1 = np.binary_repr(img.meta['quality']) == '1000000000000000000000000000000'
        #check that both levels pass and it is not a calibration file
            check = ((lev0) & (lev1))# & (calb)) 
    
        return check,img

    #J. Prchlik 2016/10/11
    #Added to give physical coordinates
    def img_extent(self,img):
    # get the image coordinates in pixels
        px0 = img.meta['crpix1']
        py0 = img.meta['crpix2']
    # get the image coordinates in arcsec 
        ax0 = img.meta['crval1']
        ay0 = img.meta['crval2']
    # get the image scale in arcsec 
        axd = img.meta['cdelt1']
        ayd = img.meta['cdelt2']
    #get the number of pixels
        tx,ty = img.data.shape
    #get the max and min x and y values
        minx,maxx = px0-tx,tx-px0
        miny,maxy = py0-ty,ty-py0
    #convert to arcsec
        maxx,minx = maxx*axd,minx*axd
        maxy,miny = maxy*ayd,miny*ayd
    
        return maxx,minx,maxy,miny
        



#Class for making AIA movies
class aia_mkmovie:

    #initialize aia_mkmovie
    def __init__(self,start,end,wav,cadence='6m',w0=1900,h0=1144,dpi=300,usehv = False,panel=False,color3=False,select=False,videowall=True,nproc=2,goes=False,wind=False,x0=0.0,y0=0.0,archive="/data/SDO/AIA/synoptic/",dfmt = '%Y/%m/%d %H:%M:%S',outf=True,synoptic=True,odir='working/',frate=10,time_stamp=True):


        #list of acceptable wavelengths
        self.awavs = ['94','131','171','193','211','304','335','1600','1700']

        #check output directory
        if isinstance(odir,str):
            self.odir = odir
        else:
            sys.stdout.write('odir must be a string')
            sys.exit(1)
 
        #format and create output directory
        if self.odir[-1] != '/': self.odir=self.odir+'/'
        if not os.path.isdir(self.odir): os.mkdir(self.odir)

        #use synoptic image checking (default = True)
        self.synoptic = synoptic

        #make sure datetime formatter is string
        if isinstance(dfmt,str):
            self.dfmt = dfmt
        else:
            sys.stdout.write('datetime formatter must be string')
            sys.exit(1)

        #check inserted start time
        if isinstance(start,datetime):
            self.start = start
        elif isinstance(start,str):
            self.start = datetime.strptime(start,dfmt)
        else:
            sys.stdout.write('Start time must be datetime object or formatted string')


        #check output file
        if isinstance(outf,str):
            self.outf = outf
        elif outf: 
            self.outf = self.start.date().strftime('%Y%m%d_%H%M')
        else:
            sys.stdout('outf must be a string or undefined')
            sys.exit(1)
 

        #check inserted end time
        if isinstance(end,datetime):
            self.end = end
        elif isinstance(end,str):
            self.end = datetime.strptime(end,dfmt)
        else:
            sys.stdout.write('End time must be datetime object or formatted string')



        #check if cadence is a string
        #if not so convert the cadence 
        #assuming it is given in seconds
        if isinstance(cadence,str):
            self.cadence = cadence
        elif isinstance(cadence,(int,float)):
            self.cadence = str(cadence)+'s'
        else:
            sys.stdout.write('Cadence must be a string, integer, or float')
            sys.exit(1)

        #check image height
        if isinstance(h0,(int,float)):
            self.h0 = h0
        else:
            sys.stdout.write('h0 must be an integer or float')
            sys.exit(1)
         
        #check image height
        if isinstance(frate,(int,float)):
            self.frate = int(frate)
        else:
            sys.stdout.write('frate must be an integer or float')
            sys.exit(1)
         
        #check image width
        if isinstance(w0,(int,float)):
            self.w0 = w0
        else: 
            sys.stdout.write('w0 must be an integer or float')
            sys.exit(1)

 
        #check dpi
        if isinstance(dpi,(int,float)):
            self.dpi = dpi
        else: 
            sys.stdout.write('dpi must be an integer or float')
            sys.exit(1)

        #download files from helioviewer (probably switch to something else)
        self.usehv = usehv
        #create a panel movie
        self.panel = panel
        #create 3 color image (default = False)
        self.color3 = color3
        self.select = select
        #number of processors to use when creating images
        if isinstance(nproc, int):
            self.nproc = nproc
        else:
            sys.stdout.write('nproc must be an integer')
            sys.exit(1)
         
        #create a goes plot
        self.goes = goes
        if not goes: self.goesdat =  Table()
        #create solar wind data plot
        self.wind = wind
        if not wind: self.aceadat = Table()
        #automatically turn on goes plot if wind plot is set
        if self.wind: self.goes = True

        #check if timestamp flag is set (Default = True)
        if isinstance(time_stamp,bool): 
            self.time_stamp = time_stamp
        else:
            sys.stdout.write('timestamp must be a boolean')
            sys.exit(1)

        #Do not let panel and goes/wind plots work together
        if ((self.panel) & (self.goes)):
            sys.stdout.write('Panel and goes plot cannot be used together. Choose wisely...')
            sys.exit(1)



        #location of SDO files
        if isinstance(archive,str):
            #make sure archive string ends in /
            if archive[-1] != '/': archive=archive+'/'
            self.archive = archive 
        else:
            sys.stdout.write('archive must be a string')
            sys.exit(1)
      

        #dimensions for videowall (over rides setting w0 and h0
        if videowall:
            self.w0 = 1900
            self.h0 = 1144

        #use a single wavelength
        self.single = False

        #check input wavelength formatting
        #check formatting assuming float or int
        if isinstance(wav,(int,float)):
            self.single = True
            self.wav  = str(int(wav))
            if ((self.panel) | (self.color3)):
                sys.stdout.write('Single wavelength cannot be used with panel or 3 color outputs')
                sys.exit(1)
            #check to make sure wavelength is allowed
            if self.wav not in self.awavs:
                sys.stdout.write('{0} not an acceptable wavelength'.format(self.wav))
                sys.exit(1)
        #check formatting assuming string      
        elif isinstance(wav,str):
            self.single = True
            self.wav = wav
            if ((self.panel) | (self.color3)):
                sys.stdout.write('Single wavelength cannot be used with panel or 3 color outputs')
                sys.exit(1)
            #check to make sure wavelength is allowed
            if self.wav not in self.awavs:
                sys.stdout.write('{0} not an acceptable wavelength'.format(self.wav))
                sys.exit(1)
        #check formatting assuming array
        elif isinstance(wav,(list,np.ndarray)):
            self.wav = []
            for i in self.wav:
                if isinstance(i,(float,int)):
                    self.wav.append(str(int(i)))
                elif isinstance(i,str):
                    self.wav.append(i)
                else:
                    sys.stdout.write('Wavelengths must be string, floats, or integers')
                    sys.exit(1) 
                #check to make sure wavelength is allowed
                if i not in self.awavs:
                    sys.stdout.write('{0} not an acceptable wavelength'.format(i))
                    sys.exit(1)

            if not ((self.panel) | (self.color3)):
                sys.stdout.write('Panel or 3 color not set for multiple wavelengths. Please specify one')
                sys.exit(1)
   

        #directory for file output
        wavapp = ''
        if len(self.wav) == 1: wavapp = '_{0}'.format(self.wav[0])
        else: for i,j in enumerate(self.wav):  wavapp = wavapp+'_{0}'.format(j)
        self.sdir = self.start.date().strftime('%Y%m%d_%H%M')+wavapp

#create directories without erroring if they already exist c
    def create_dir(self,dirs):
        try:
            os.mkdir(dirs)
        except OSError:
            sys.stdout.write('{0} Already Exists'.format(dirs))

    

    def gather_files(self):
        # use helioviewer if requested 
        if self.usehv:
            from sunpy.net.helioviewer import HelioviewerClient
            import matplotlib.image as mpimg
            hv = HelioviewerClient()
            dayarray = glob.glob(self.sdir+'/raw/*jp2')
            forpool = np.arange(len(dayarray))
            #for i in forpool: format_img(i)
            pool2 = Pool(processes=nproc)
            outs = pool2.map(get_file,forpool)
            pool2.close()

#datasources = hv.get_data_sources()


        #video wall ratio
        self.rv = float(self.w0)/float(self.h0)


        #scale up the images with increasing dpi
        self.sc = self.dpi/100

        self.span = (self.end-self.start).seconds #seconds to run the movie over




        #create a directory which will contain the raw png files
        #sdir = stard+eday.date().strftime('%Y%m%d')
        #creating a subdirectory to extra step is not need
        dirlist = [self.sdir,self.sdir+'/raw',self.sdir+'/working',self.sdir+'/working/symlinks',self.sdir+'/final',self.sdir+'/goes',self.sdir+'/ace']
        for i in dirlist: self.create_dir(i)

        

        #get all days in date time span
        if self.goes: 
            ggxf.look_xrays(sday,now+dt(days=1),self.sdir)
            goesfil = glob.glob(self.sdir+'/goes/*txt')
            goesnames = [ 'YR', 'MO', 'DA', 'HHMM', 'JDay', 'Secs', 'Short', 'Long'] 
            self.goesdat = Table(names=goesnames)
        
        #loop over all day information and add to large array
            for m in goesfil:
                temp = ascii.read(m,guess=True,comment='#',data_start=2,names=goesnames)
                self.goesdat = vstack([self.goesdat,temp])
        
            #create datetime array
            self.goesdat['time_dt'] = [datetime(int(i['YR']),int(i['MO']),int(i['DA']))+dt(seconds=i['Secs']) for i in self.goesdat]
        
        if self.wind:
            aceb = glob.glob(sdir+'/ace/*mag*txt')
            acep = glob.glob(sdir+'/ace/*swe*txt')
        
            aceb_names = [ 'YR', 'MO', 'DA', 'HHMM', 'JDay', 'Secs', 'S', 'Bx','By','Bz','Bt','Lat','Long'] 
            acep_names = [ 'YR', 'MO', 'DA', 'HHMM', 'JDay', 'Secs', 'S', 'Den','Speed','Temp'] 
          
            acebdat = Table(names=aceb_names)
            acepdat = Table(names=acep_names)
        
        #put B field in large array
            for m in aceb:
                temp = ascii.read(m,guess=True,comment='#',data_start=2,names=aceb_names)
                acebdat = vstack([acebdat,temp])
        #put plasmag in large array
            for m in acep:
                temp = ascii.read(m,guess=True,comment='#',data_start=2,names=acep_names)
                acepdat = vstack([acepdat,temp])
        
        
            self.aceadat = join(acepdat,acebdat,keys=['YR','MO','DA','HHMM'])
            #create datetime array
            self.aceadat['time_dt'] = [datetime(int(i['YR']),int(i['MO']),int(i['DA']))+dt(seconds=i['Secs_1']) for i in self.aceadat]
        


        #J. Prchlik 2016/10/06
        #Updated version calls local files
        verbose=False
        debug = False
        src = Scream(archive=self.archive,verbose=verbose,debug=debug)
        ##########################################################
        # Phase 1: get file names                                #
        ##########################################################
        sendspan = "-{0:1.0f}s".format(self.span) # need to spend current span not total span
        paths = src.get_paths(date=self.end.strftime("%Y-%m-%d"), time=self.end.strftime("%H:%M:%S"),span=sendspan)


        if self.single:
            fits_files = src.get_filelist(date=self.end.strftime("%Y-%m-%d"),time=self.end.strftime("%H:%M:%S"),span=sendspan,wavelnth=self.wav)
            qfls, qtms = src.run_quality_check(synoptic=self.synoptic)
            self.fits_files = src.get_sample(files = qfls, sample = self.cadence, nfiles = 1)
        else:
            self.fits_files = []
           #loop over all wavelengths in array
            for i in self.wav:
                fits_files = src.get_filelist(date=self.end.strftime("%Y-%m-%d"),time=self.end.strftime("%H:%M:%S"),span=sendspan,wavelnth=i)
                qfls, qtms = src.run_quality_check(synoptic=self.synoptic)
                self.fits_files.append(src.get_sample(files = qfls, sample = self.cadence, nfiles = 1))

        for i in self.fits_files:
            print i
            newfile = i.split('/')[-1]
            try:
                os.symlink(i,self.sdir+'/raw/'+newfile)
            except OSError:
                continue
        


    def create_images_movie(self):


        #create a list of class objects
        image_list = [aia_mkimage(i,sday=False,eday=False,w0=self.w0,h0=self.h0,dpi=self.dpi,sc=self.sc,goes=self.goes,goesday=self.goesdat,
                      ace=self.wind,aceadat=self.aceadat,single=self.single,panel=self.panel,color3=self.color3,time_stamp=self.time_stamp,odir=self.sdir+'/working/') for i in self.fits_files]

        #J. Prchlik 2016/10/06
        #Switched jp2 to fits
        #loop is for testing purposes
        #for i in forpool: format_img(i)
        if self.nproc > 1:
            pool1 = Pool(processes=self.nproc)
            outs = pool1.map(format_img,image_list)
            pool1.close()
        #just loop is 1 processor specified
        else:
            for i in forpool: format_img(i)


        create_movie(odir = 'final/',pdir = self.sdir, ext = 'png', w0 = self.w0, h0=self.h0,frate=self.frate,outmov=self.outf)

    def run_all(self):
        
        self.gather_files()
        self.create_images_movie()
 


def format_img(aia_img):
    aia_img.format_img()



    


        
        
