import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle



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


def makePlot(a,d,h):

    np.random.seed(198964)
    print(a)

    figure=plt.figure(figsize=(10,6),dpi=100)
    ax=figure.add_subplot(111)

    xmax=0
    ymax=0
    n=len(a)

    for i in range(n):
        #h=a[i]
        #yi=[i, i,  i+h, i+h, i]
        '''
        xi=a[i]+np.array([0, d, d, 0, 0])+1
        #xi=np.sqrt(xi)
        y0=np.sqrt(i+1)
        #y0=i+1
        yi=y0+np.array([0, 0, h, h, 0])
        ax.plot(xi,yi,color='k')
        xmax=max(np.max(xi+d+1), xmax)
        ymax=max(np.max(yi+h+1), ymax)
        '''

        xi=a[i]
        #yi=np.sqrt(i+1)
        yi=i
        #yi=(i+1)**0.89
        hii=np.random.random()*h+h
        alphaii=0.3+0.7*i/float(n-1)
        pii=Rectangle((xi,yi), width=d, height=hii, edgecolor='k',
                color='royalblue',
                alpha=alphaii)
        print('alphaii=',alphaii)
        ax.add_patch(pii)

        xmax=max(xi+d+1, xmax)
        ymax=max(yi+h+1, ymax)

    ax.set_aspect('equal')
    ax.set_xlim([0,xmax])
    ax.set_ylim([0,ymax])
    #ax.set_xscale('log')
    #ax.set_yscale('log')
    ax.set_axis_off()



    plot_save_name='./recaman_stairs_n_%d' %n
    print '\n# <recman2>: Save figure to', plot_save_name
    figure.savefig(plot_save_name+'.png',dpi=100,bbox_inches='tight')
    figure.savefig(plot_save_name+'.eps',dpi=100,bbox_inches='tight')

    #plt.show(block=False)
    plt.close(figure)



if __name__=='__main__':

    #N=65
    for nii in [33,66]:
        a=getSequence(nii)
        d=0.5
        h=2.4
        makePlot(a,d,h)

