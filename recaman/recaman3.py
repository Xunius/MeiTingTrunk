import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import numpy as np

N=49

def getSequence(n):
    a=[]
    for i in range(n):
        if i==0:
            ri=0
        else:
            t=a[i-1]-i
            if t>0 and t not in a:
                ri=t
            else:
                ri=a[i-1]+i
        a.append(ri)
    #a.insert(0,0)

    return a


def makePlot(a,lw):

    figure=plt.figure(figsize=(8,10),dpi=100)
    ax=figure.add_subplot(111)

    n=len(a)
    xs=[]
    ys=[]
    maxy=0
    miny=0

    maxx=0
    minx=0

    d=0.2

    for i in range(n-1):

        x0=a[i]
        x1=a[i]
        x2=a[i+1]
        x3=a[i+1]
        y0=0
        y3=0
        y1=abs(x3-x0)*0.5
        if i%2==1:
            y1=-y1
            sign=-1
        else:
            sign=1
        y2=y1

        if x2>x0:
            signx=1
        else:
            signx=-1

        xsii=[x0-signx*d, x1-signx*d, x2+signx*d, x3+signx*d, x3-signx*d,
                x3-signx*d, x1+signx*d, x0+signx*d]
        ysii=[y0, y1+sign*d, y2+sign*d, y3, y3, y2-sign*d, y1-sign*d, y0]
        xy=np.vstack([xsii,ysii]).T
        print 'xy',xy

        maxy=max(maxy,np.max(ysii))
        miny=min(miny,np.min(ysii))
        maxx=max(maxx,np.max(xsii))
        minx=min(minx,np.min(xsii))

        rec1=Polygon(xy, closed=True, fill='royalblue', edgecolor='none')
        ax.add_patch(rec1)
        #alphaii=0.3+0.7*i/float(n-2)
        #lwii=lw
        #lwii=1.
        #print('alphaii=',alphaii,'lwii=',lwii)
        #lii,=ax.plot(xsii,ysii,color='royalblue',
                #linewidth=lwii,
                #alpha=alphaii)
        #lii.set_solid_capstyle('butt')

        '''
        if i==0:
            xs.extend([x0,x1,x2,x3])
            ys.extend([y0,y1,y2,y3])
        else:
            xs.extend([x1,x2,x3])
            ys.extend([y1,y2,y3])
        '''

    '''
    lii,=ax.plot(ys,xs,color='royalblue',
            linewidth=lw,
            alpha=1.)
    lii.set_solid_capstyle('butt')
    '''

    ax.set_aspect('equal')
    ax.set_xlim([minx-d,maxx+d])
    ax.set_ylim([miny-d,maxy+d])
    ax.set_axis_off()


    #----------------- Save plot------------
    plot_save_name='./recaman_box_n_%d_fillline' %n
    print('\n# <recman>: Save figure to', plot_save_name)
    figure.savefig(plot_save_name+'.png',dpi=100,bbox_inches='tight')
    figure.savefig(plot_save_name+'.eps',dpi=100,bbox_inches='tight')

    #plt.show(block=False)
    plt.close(figure)


if __name__=='__main__':


    # n=33 and n=66 are 2 about-to-leap points
    nii=33
    a=getSequence(nii)
    print(a)

    makePlot(a,4.0)

    '''
    nii=66
    a=getSequence(nii)
    print(a)

    makePlot(a,2.4)
    '''
