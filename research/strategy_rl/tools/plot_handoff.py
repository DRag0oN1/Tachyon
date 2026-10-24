"""Plot saved frozen-policy intervention results without running a policy."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def plot(root):
    data=json.loads((root/'analysis.json').read_text())
    names=list(data['effects'])
    labels=['Speed .75 → 2.1 m/s','Reach .32 → .60 m','Acquire 3.0 → 1.4 s',
            'Place 2.4 → 1.1 s','Acquire success .72 → .96','Place success .72 → .96','Turn .65 → .25 s']
    differences=np.array([data['effects'][n]['confirmation']['meanScoreDifference'] for n in names])
    intervals=np.array([data['effects'][n]['confirmation']['difference95CI'] for n in names])
    colors=['#187e88' if data['effects'][n]['replicatedMaterialEffect'] else '#9da4ad' for n in names]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,(effect,profiles)=plt.subplots(1,2,figsize=(12.5,5.4),layout='constrained',gridspec_kw={'width_ratios':[1.65,1]})
    positions=np.arange(len(names))
    effect.barh(positions,differences,color=colors,height=.65)
    effect.errorbar(differences,positions,xerr=np.stack([differences-intervals[:,0],intervals[:,1]-differences]),
                    fmt='none',ecolor='#243344',capsize=3,linewidth=1.2)
    effect.set_yticks(positions,labels); effect.invert_yaxis()
    effect.axvline(0,color='#5b6470',linewidth=1)
    effect.axvline(2,color='#777',linewidth=1,linestyle='--',label='2-point materiality threshold')
    effect.set(xlabel='Confirmation difference in modeled points',title='Single-feature diagnostics · 96 episodes / cell')
    effect.legend(frameon=False,loc='lower right',fontsize=9)
    profiles_list=['profile_balanced','profile_drive_priority','profile_handling_priority','profile_reach_priority']
    means=np.array([data['summaries']['confirmation'][n]['meanScore'] for n in profiles_list])
    ci=np.array([data['summaries']['confirmation'][n]['score95CI'] for n in profiles_list])
    y=np.arange(4)
    profiles.scatter(means,y,s=75,color=['#9da4ad','#9da4ad','#187e88','#9da4ad'])
    profiles.errorbar(means,y,xerr=np.stack([means-ci[:,0],ci[:,1]-means]),fmt='none',ecolor='#243344',capsize=3)
    profiles.set_yticks(y,['Balanced (blind)','Drive priority','Handling (selected)','Reach priority']); profiles.invert_yaxis()
    profiles.set(xlabel='Mean modeled points (zoomed axis)',xlim=(37,44.5),title='Fixed feasible abstract profiles\n16 episode-seed blocks per profile')
    for axis in (effect,profiles): axis.grid(axis='x',alpha=.15); axis.set_axisbelow(True)
    fig.suptitle('Tachyon · frozen-policy capability evidence · abstract simulation only',weight='bold',fontsize=14)
    fig.savefig(root/'capability-effects.png',dpi=170,bbox_inches='tight',pad_inches=.15)
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('root',type=Path)
    plot(parser.parse_args().root)
