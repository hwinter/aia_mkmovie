__version__ = "0.0.1 (2017/07/24)"
__authors__ = ['Jakub Prchlik <jakub.prchlik@cfa.harvard.edu>']
__email__   = "jakub.prchlik@cfa.harvard.edu"


import matplotlib
##fixes multiprocess issue (scrambled text in images)
matplotlib.use('agg',warn=False,force=True)
import sys

try:
    import sunpy.map
    from sunpy.cm import cm
except ImportError:
    sys.stdout.write(sys.stderr,"sunpy not installed, use pip install sunpy --upgrade")

from matplotlib.transforms import Bbox
import matplotlib.dates as mdates
import subprocess
import glob
import os
import stat
import numpy as np
from datetime import date,datetime
from datetime import timedelta as dt
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid.inset_locator import inset_axes
from astropy.io import ascii
from astropy.table import vstack,Table,join
from sunpy.instr.aia import aiaprep as ap

class aia_mkimage:

    def __init__(self,dayarray,sday=False,eday=False,w0=1900.,h0=1200.,dpi=100.,sc=1.,
                 goes=False,goesdat=False,ace=False,aceadat=False,single=True,panel=False,
                 color3=False,time_stamp=True,odir='working/',cutout=False,
                 img_scale=None,cx=0.,cy=0.,xlim=None,ylim=None,synoptic=False,rot_time=None,aiaprep=True):

        """
        Day array if 3 color goes in as RGB
        Day array if panel goes in as Top left, top right, bottom left, bottom right 
        """
        #check format of input day array
        if isinstance(dayarray,list):
            self.dayarray = dayarray
            if len(dayarray) == 3: color3 = True #automatically assume rgb creation if 3 
            elif len(dayarray) == 4: panel = True #automatically assume panel creation if 4 
            elif len(dayarray) == 1: color3 = False #force color 3 to be false if length 1 array
            else:
                sys.stdout.write('dayarray must be length 1 (single), 3 (rgb), or 4 (panel)')
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

        #check if synoptic flag is set
        if isinstance(synoptic,bool):  
            self.synoptic = synoptic
        else:
            sys.stdout.write('synoptic must be a boolean')
            sys.exit(1)

        #check if aiaprep flag is set
        if isinstance(aiaprep,bool):
            self.aiaprep = aiaprep
        else:
            sys.stdout.write('aiaprep must be boolean (Default = True)')
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
        elif isinstance(aceadat,list):
            self.aceadat = [] #do not plot goes data
        else:
            sys.stdout.write('acedat must be a astropy table')
            sys.exit(1)

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

        #check format of goesdat Table if it exits 
        if isinstance(goesdat,Table):
            self.goesdat = goesdat
        elif goesdat == False:
            self.goesdat = [] #do not plot goes data
        else:
            sys.stdout.write('goesdat must be a astropy table')

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

        #rotate image if h0 > w0
        self.flip_image = False
        #Can do with out checking since we already checked w0,h0 are numbers
        if h0 > w0:
            self.h0 = w0
            self.w0 = h0
            self.flip_image = True

       #check if cutout flag is set (Default = False)
        if isinstance(cutout,bool):
            self.cutout = cutout
        else:
            sys.stdout.write('cutout must be a boolean')
            sys.exit(1)


        #check inserted rot_time time
        if isinstance(rot_time,datetime):
            self.rot_time = rot_time
            self.rotation = True
        elif isinstance(rot_time,str):
            self.rot_time = datetime.strptime(rot_time,dfmt)
            self.rotation = True
        elif rot_time is None:
            self.rot_time = rot_time
            self.rotation = False
        else:
            sys.stdout.write('rot_time must be datetime object or formatted string')
            sys.exit(1)



        #check image x center
        if isinstance(cx,(int,float)):
            self.cx = cx
        else:
            sys.stdout.write('cx must be an integer or float (Assuming 0)')
            self.cx = 0.0
        
        #check image y center
        if isinstance(cy,(int,float)):
            self.cy = cy
        else:
            sys.stdout.write('cy must be an integer or float (Assuming 0)')
            self.cy = 0.0     

 


 
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
        if img_scale is None:
            self.img_scale = {'0094':[cm.sdoaia94  ,np.arcsinh(1.),np.arcsinh(150.)],
                              '0131':[cm.sdoaia131 ,np.arcsinh(1.),np.arcsinh(500.)],
                              '0171':[cm.sdoaia171 ,np.arcsinh(10.),np.arcsinh(2500.)],
                              '0193':[cm.sdoaia193 ,np.arcsinh(100.),np.arcsinh(4500.)],
                              '0211':[cm.sdoaia211 ,np.arcsinh(10.),np.arcsinh(4000.)],
                              '0304':[cm.sdoaia304 ,np.arcsinh(2.),np.arcsinh(300.)],
                              '0335':[cm.sdoaia335 ,np.arcsinh(1.),np.arcsinh(100.)],
                              '1600':[cm.sdoaia1600,np.arcsinh(20.),np.arcsinh(500.)],
                              '1700':[cm.sdoaia1700,np.arcsinh(200.),np.arcsinh(4000.)]}
        elif isinstance(img_scale,dict):
            self.img_scale = img_scale
        else:
            sys.stdout.write('img_scale must be a dictionary with color map, min value, max value')
            sys.exit(1)
    


        #check proposed x and y limits
        if ((xlim is None) & (ylim is None) & (not self.rotation)):
            self.cutout = False
        #if you are rotating assume a cut out (no reason to rotate with full sun)
        elif (self.rotation):
            self.cutout = True 
        #make sure 
        #make sure 
        elif ((xlim is not None) & (isinstance(xlim,(np.ndarray,list))) & (ylim is not None) & (isinstance(ylim,(np.ndarray,list)))):
            for i in xlim:
                if not isinstance(i,(float,int)):
                    sys.stdout.write('Individual x values must be float or int')
                    sys.exit(1)
            #if passes set xlim
            #self.xlim = xlim

            for i in ylim:
                if not isinstance(i,(float,int)):
                    sys.stdout.write('Individual y values must be float or int')
                    sys.exit(1)
            #if passes set ylim
            #self.ylim = ylim
        else: 
            sys.stdout.write('X and Y limits must be empty, lists, or numpy arrays')
            sys.exit(1)

 
   #create window for plotting
    def sub_window(self):

      #3 color image
       if self.color3:
           self.scale = [self.img.scale[0].value,self.img.scale[1].value] # get x, y image scale
       #single color image
       else:
           self.scale = [self.img.scale[0].value,self.img.scale[1].value] # get x, y image scale

       #if rotation set get modify cx and cy values
       if self.rotation:
           from sunpy.physics.differential_rotation import rot_hpc
           import astropy.units as u
           #rotate start points
           cx, cy = rot_hpc(self.cx*u.arcsec,self.cy*u.arcsec,self.rot_time,self.obs_time)
           #update with new rotation values
           self.cx, self.cy = cx.value,cy.value

       #set new plot limits
       #flip x and y values if h0>w0
       if self.flip_image:
           self.xlim = [self.cy-(self.scale[0]*self.w0/2.),self.cy+(self.scale[0]*self.w0/2.)]
           self.ylim = [self.cx-(self.scale[1]*self.h0/2.),self.cx+(self.scale[1]*self.h0/2.)]
       else:
           self.xlim = [self.cx-(self.scale[0]*self.w0/2.),self.cx+(self.scale[0]*self.w0/2.)]
           self.ylim = [self.cy-(self.scale[1]*self.h0/2.),self.cy+(self.scale[1]*self.h0/2.)]


    #for j,i in enumerate(dayarray):
    #reformat file to be in 1900x1200 array and contain timetext
    def format_img(self):
    
            #input fits file
            self.filep = self.dayarray
          
        	
            #check image quality
            check, img = self.qual_check()
           
            #return image wavelength
            #if isinstance(img,list):
            if self.color3:
                self.wav = []
                img3d = np.zeros((img[0].data.shape[0],img[0].data.shape[1],3))
                for j,i in enumerate(img):
                    self.wav.append('{0:4.0f}'.format(i.wavelength.value).replace(' ','0'))
                    #set normalized scaling for every observation
                    ivmin = self.img_scale[self.wav[j]][1]
                    ivmax = self.img_scale[self.wav[j]][2]
                    prelim = (np.arcsinh(i.data/i.exposure_time.value)-ivmin)/ivmax
            
                    #replace out of bounds points
                    prelim[prelim < 0.] = 0.
                    prelim[prelim > 1.] = 1.
   
                    #if flipped image flip the x,y values in prelim
                    if self.flip_image:
                        img3d[:,:,j] = prelim.T
                    else:
                        img3d[:,:,j] = prelim
                #output png file
                outfi = self.odir+'AIA_{0}_'.format(img[0].date.strftime('%Y%m%d_%H%M%S'))+'{0}_{1}_{2}.png'.format(*self.wav)
                #observed time 
                self.obs_time = img[0].date
                #set scale for plotting 
                self.scale = [self.img.scale[0].value,self.img.scale[1].value] # get x, y image scale 
            #set up panel plot parameters
            elif self.panel:
                ivmin = {}
                ivmax = {}
                icmap = {}
                self.wav = []
                #put parameters in a series of dictionaries
                for j,i in enumerate(img):
                    self.wav.append('{0:4.0f}'.format(i.wavelength.value).replace(' ','0'))
                    icmap[self.wav[j]] = self.img_scale[self.wav[j]][0]
                    ivmin[self.wav[j]] = self.img_scale[self.wav[j]][1]
                    ivmax[self.wav[j]] = self.img_scale[self.wav[j]][2]
                outfi = self.odir+'AIA_{0}_'.format(img[0].date.strftime('%Y%m%d_%H%M%S'))+'{0}_{1}_{2}_{3}.png'.format(*self.wav)
                #set scale for plotting 
                self.scale = [self.img.scale[0].value,self.img.scale[1].value] # get x, y image scale 
                #observed time 
                self.obs_time = img[0].date
            else:
                self.wav ='{0:4.0f}'.format( img.wavelength.value).replace(' ','0')
                #use default color tables
                icmap = self.img_scale[self.wav][0]
                ivmin = self.img_scale[self.wav][1]
                ivmax = self.img_scale[self.wav][2]
                outfi = self.odir+'AIA_{0}_'.format(img.date.strftime('%Y%m%d_%H%M%S'))+'{0}.png'.format(self.wav)
                #set scale for plotting 
                self.scale = [self.img.scale[0].value,self.img.scale[1].value] # get x, y image scale 
                #observed time 
                self.obs_time = img.date


            #set up subwindow limits if cutout set
            if self.cutout: self.sub_window()

            #see if output file already exists
            test = os.path.isfile(outfi)
        
        #test to see if png file already exists and passes quality tests
            if ((test == False) & (check)):
                print 'Modifying file '+outfi
        		# J. Prchlik 2016/10/06
        #Block add J. Prchlik (2016/10/06) to give physical coordinate values 

                #set up extra in stuff in plot if panel set
                if self.panel:
                    fig,ax = plt.subplots(figsize=(self.sc*float(self.w0)/float(self.dpi),self.sc*float(self.h0)/float(self.dpi)),nrows=2,ncols=2)
                    #remove space between plots
                    fig.subplots_adjust(wspace=0.0001,hspace=0.0001)
                    #make axis object a 1D array
                    ax = ax.ravel()
                    img = sunpy.map.Map(*self.filep)
                    
                    #set up dictionary for plotting data
                    img_dict = {} 
                    for l,p in enumerate(self.wav): img_dict[p] = img[l]
                #single image properties
                else:
                    fig,ax = plt.subplots(figsize=(self.sc*float(self.w0)/float(self.dpi),self.sc*float(self.h0)/float(self.dpi)))
                    img = sunpy.map.Map(*self.filep)
                    ax.set_axis_off()
              
                #universal image properties 
                fig.set_dpi(self.dpi)
                fig.subplots_adjust(left=0,bottom=0,right=1,top=1)

                #return extent of image
                #use the first image in the list if it is a composite image to get the image boundaries
                if isinstance(img,list):
                    maxx,minx,maxy,miny = self.img_extent(img[0])
                #else use the only image
                else:
                    maxx,minx,maxy,miny = self.img_extent(img)


                

                #set text location
                if ((self.w0 > self.h0) & (not self.cutout)):
                    txtx = -(self.w0-self.h0)
                    txty = (maxy-miny)*0.01
                elif ((self.w0 < self.h0) & (not self.cutout)):
                    txty = -(self.h0-self.w0)
                    txtx = (maxx-minx)*0.01
                elif ((self.w0 == self.h0) & (not self.cutout)):
                    txtx = (maxx-minx)*0.01
                    txty = (maxy-miny)*0.01
                elif ((self.cutout) | (self.panel)):
                    txtx = (max(self.xlim)-min(self.xlim))*0.01+(min(self.xlim)-minx)
                    txty = (max(self.ylim)-min(self.ylim))*0.01+(min(self.ylim)-miny)

                #set the origin location
                origin = 'lower'

        #plot the image in matplotlib
                #use color composite image if color3 set
                if self.color3:
                    ax.imshow(img3d,interpolation='none',origin=origin,extent=[minx,maxx,miny,maxy],aspect='auto')
                    ax.text(minx+txtx,miny+txty,'AIA {0}/{1}/{2}'.format(*self.wav)+'- {0}Z'.format(img[0].date.strftime('%Y/%m/%d - %H:%M:%S')),color='white',fontsize=36,zorder=5000,fontweight='bold')
                #loop through axis objects if panel
                elif self.panel:
                    #see if image is flipped
                    if self.flip_image:
                        for l,p in enumerate(self.wav): ax[l].imshow(np.arcsinh(img_dict[p].data.T/img_dict[p].exposure_time.value),interpolation='none',cmap=icmap[p],origin=origin,vmin=ivmin[p],vmax=ivmax[p],extent=[minx,maxx,miny,maxy],aspect='auto')
                    else:
                        for l,p in enumerate(self.wav): ax[l].imshow(np.arcsinh(img_dict[p].data/img_dict[p].exposure_time.value),interpolation='none',cmap=icmap[p],origin=origin,vmin=ivmin[p],vmax=ivmax[p],extent=[minx,maxx,miny,maxy],aspect='auto')
                    #put text in lower left axis
                    ax[2].text(minx+txtx,miny+txty,'AIA {0}/{1}/{2}/{3}'.format(*self.wav)+'- {0}Z'.format(img[0].date.strftime('%Y/%m/%d - %H:%M:%S')),color='white',fontsize=24,zorder=5000,fontweight='bold')
                else:
                    #see if image is flipped
                    if self.flip_image: ax.imshow(np.arcsinh(img.data.T/img_dict[p].exposure_time.value),interpolation='none',cmap=icmap,origin=origin,vmin=ivmin,vmax=ivmax,extent=[minx,maxx,miny,maxy],aspect='auto')
                    else: ax.imshow(np.arcsinh(img.data/img_dict[p].exposure_time.value),interpolation='none',cmap=icmap,origin=origin,vmin=ivmin,vmax=ivmax,extent=[minx,maxx,miny,maxy],aspect='auto')
                    ax.text(minx+txtx,miny+txty,'AIA {0} - {1}Z'.format(self.wav,img.date.strftime('%Y/%m/%d - %H:%M:%S')),color='white',fontsize=36,zorder=5000,fontweight='bold')
                #set limits for cutout
                if self.cutout:
                    #loop through all if panel
                    if self.panel:
                        for iax in ax:
                            iax.set_xlim(self.xlim)
                            iax.set_ylim(self.ylim)
                            iax.set_axis_off()
                        
                    #if not panel use a single axis 
                    else:
                        ax.set_xlim(self.xlim)
                        ax.set_ylim(self.ylim)


                if ((self.goes) & (not self.panel)):
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
            for k,i in enumerate(img):
                #prep images if aiaprep is set
                if self.aiaprep: img[k] = ap(img[k]) 
                #exit if check ever fails
                if check:
                    lev0 = i.meta['quallev0'] == 0
                #check level1 bitwise keywords (http://jsoc.stanford.edu/doc/keywords/AIA/AIA02840_K_AIA-SDO_FITS_Keyword_Document.pdf)
                #for synoptic 1024x1024
                    if self.synoptic:
                        lev1 = np.binary_repr(img.meta['quality']) == '1000000000000000000000000000000'
                    else:
                   #4096x4096
                       lev1 = i.meta['quality'] == 0
                   #check that both levels pass and it is not a calibration file
                       check = ((lev0) & (lev1))# & (calb)) 
                #leave loop when check fails
                else: 
                    continue
            #set default image to be the first image
            #create an image object to get parameters from
            self.img = img[0] 
        else:
            #prep images if aiaprep is set
            if self.aiaprep: img = ap(img) 
            #create an image object to get parameters from
            self.img = img 
          
            lev0 = img.meta['quallev0'] == 0
        #check level1 bitwise keywords (http://jsoc.stanford.edu/doc/keywords/AIA/AIA02840_K_AIA-SDO_FITS_Keyword_Document.pdf)
        #for synoptic 1024x1024
            if self.synoptic:
                lev1 = np.binary_repr(img.meta['quality']) == '1000000000000000000000000000000'
            else:
                #4096x4096
                lev1 = img.meta['quality'] == 0
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
        pminx,pmaxx = 0.-px0,tx-px0
        pminy,pmaxy = 0.-py0,ty-py0

        #convert to arcsec
        #Also flip the x and y values if h0 > w0
        if self.flip_image:
            maxy,miny = ax0+pmaxx*axd,ax0+pminx*axd
            maxx,minx = ay0+pmaxy*ayd,ay0+pminy*ayd
        else:
            maxx,minx = ax0+pmaxx*axd,ax0+pminx*axd
            maxy,miny = ay0+pmaxy*ayd,ay0+pminy*ayd
    
        return maxx,minx,maxy,miny
        



