import matplotlib.pyplot as plt

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

    for i in range(n-1):
        '''
        x0=a[i]
        x2=a[i+1]
        x1=0.5*(x0+x2)
        y0=0
        y2=0
        y1=abs(x2-x0)*0.5
        if i%2==0:
            y1=-y1
        ax.plot([x0,x1,x2],[y0,y1,y2],color='0.6')
        '''
        x0=a[i]
        x1=a[i]
        x2=a[i+1]
        x3=a[i+1]
        y0=0
        y3=0
        y1=abs(x3-x0)*0.5
        if i%2==1:
            y1=-y1
        y2=y1

        #colorii=str(0.8-0.7*i/float(N-1))
        #print('colorii',colorii)
        alphaii=0.3+0.7*i/float(n-2)
        #lwii=1.0+1.*i/float(n-1)
        lwii=lw
        print('alphaii=',alphaii,'lwii=',lwii)
        lii,=ax.plot([y0,y1,y2,y3],[x0,x1,x2,x3],color='royalblue',
                linewidth=lwii,
                alpha=alphaii)
        lii.set_solid_capstyle('butt')

    ax.set_aspect('equal')
    #ax.set_xlim([0,282])
    ax.set_axis_off()


    #----------------- Save plot------------
    plot_save_name='./recaman_box_n_%d' %n
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
