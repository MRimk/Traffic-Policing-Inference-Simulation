import pandas as pd
import matplotlib.pyplot as plt


def get_bdp(xtopo: bool = False): 
    link_count = 3 if xtopo else 2
    outRate = 2 * 10**6 # 2 Mbps
    rtt = 5 * link_count * 2 * 10**-3 # 5ms one link, total return time is 20ms
    bdp = outRate * rtt / 8 # 2Mbps / 8b * 20ms = 5000B
    return bdp

def clean_colums(df, xtopo = False):
    bdp = get_bdp(xtopo)
    mtu = 1500
    df['queue_size'] = df['queue_size'].str.rstrip('B').astype(float)
    df['queue_size'] = df['queue_size'] / bdp
    df['burst'] = (df['burst'].astype(float) / mtu).astype(str) + "p"
    df['actual_rate_mbps'] = df['actual_rate'] / 1e6  # Convert to Mbps
    df['rate_mbps'] = df['rate'] / 1e6  # Convert to Mbps
    df['rx_rate_mbps'] = df['rx_rate'] / 1e6  # Convert to Mbps
    df['diff_mbps'] =  df['rate_mbps'] - df['rx_rate_mbps'] # df['rate_mbps'] - df['actual_rate_mbps']
    df['error_rate'] = df['diff_mbps'] / df['rx_rate_mbps']
    return df

def plot_throughput(df, log=True, y_min=None, y_max=None, keep_fixed=True, title=None):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for burst, group in df.groupby('burst'):
        g = group.sort_values('queue_size')
        ax.plot(g['queue_size'], g['rx_rate_mbps'],
                marker='o', label=f'Burst {burst}')

    
    ax.set_xlabel('Queue Size (BDP)')
    ax.set_ylabel('Actual Rate (Mbps)')
    if title is not None:
        ax.set_title(title)
    else:
        ax.set_title('Actual Rate vs Queue Size for Different Burst Sizes')
    if log:
        ax.set_xscale('log')
    ax.grid(True, which='both', linestyle='--')
    ax.legend()
    
    
    if y_min is not None or y_max is not None:
        # current limits in case one side is left as None
        cur_low, cur_high = ax.get_ylim()
        low  = cur_low  if y_min is None else y_min
        high = cur_high if y_max is None else y_max
        ax.set_ylim(low, high)
        if keep_fixed:
            ax.autoscale(enable=False, axis='y')  # freeze it

    fig.tight_layout()
    plt.show()

def plot_estimated_rate(df, log=True, y_min=None, y_max=None, keep_fixed=True, title=None):
    fig, ax = plt.subplots(figsize=(10, 6))

    
    for burst, group in df.groupby('burst'):
        group_sorted = group.sort_values('queue_size')
        ax.plot(group_sorted['queue_size'], group_sorted['rate_mbps'],
                marker='o', label=f'Burst {burst}')

    ax.set_xlabel('Queue Size (BDP)')
    ax.set_ylabel('Estimated Rate (Mbps)')
    if title is not None:
        ax.set_title(title)
    else:
        ax.set_title('Estimated rate vs Queue Size for Different Burst Sizes')
    if log:
        ax.set_xscale('log')  # Optional: log scale for wide range
    ax.grid(True, which='both', linestyle='--')
    ax.legend()
    
    if y_min is not None or y_max is not None:
        # current limits in case one side is left as None
        cur_low, cur_high = ax.get_ylim()
        low  = cur_low  if y_min is None else y_min
        high = cur_high if y_max is None else y_max
        ax.set_ylim(low, high)
        if keep_fixed:
            ax.autoscale(enable=False, axis='y')  # freeze it

    
    fig.tight_layout()
    plt.show()

def plot_error_rate(df, y_min=None, y_max=None, keep_fixed=True):
    fig, ax = plt.subplots(figsize=(10, 6))

    for burst, group in df.groupby('burst'):
        group_sorted = group.sort_values('queue_size')
        ax.plot(group_sorted['queue_size'], group_sorted['error_rate'],
                marker='o', label=f'Burst {burst}')

    ax.set_xlabel('Queue Size (BDP)')
    ax.set_ylabel('Error Rate')
    ax.set_title('Error Rate vs Queue Size for Different Burst Sizes')
    ax.set_xscale('log')  # Optional: log scale for wide range
    ax.grid(True, which='both', linestyle='--')
    ax.legend()
    
    if y_min is not None or y_max is not None:
        # current limits in case one side is left as None
        cur_low, cur_high = ax.get_ylim()
        low  = cur_low  if y_min is None else y_min
        high = cur_high if y_max is None else y_max
        ax.set_ylim(low, high)
        if keep_fixed:
            ax.autoscale(enable=False, axis='y')  # freeze it
    
    fig.tight_layout()
    plt.show()
    
def plot_throughput_difference(df, y_min=None, y_max=None, keep_fixed=True):
    fig, ax = plt.subplots(figsize=(10, 6))

    for burst_val, grp in df.groupby('burst'):
        # sort by queue_size so lines connect in order
        grp = grp.sort_values('queue_size')
        ax.plot(grp['queue_size'], grp['diff_mbps'], marker='o', label=f'burst={int(burst_val)}')

    ax.set_xlabel('Queue Size (BDP)')
    ax.set_ylabel('Rate - Actual Rate (Mbps)')
    ax.set_title('Impact of Queue Size & Burst on Rate Difference')
    ax.set_xscale('log')  
    ax.grid(True, which='both', linestyle='--')
    ax.legend(title='Burst Size')
    
    if y_min is not None or y_max is not None:
        # current limits in case one side is left as None
        cur_low, cur_high = ax.get_ylim()
        low  = cur_low  if y_min is None else y_min
        high = cur_high if y_max is None else y_max
        ax.set_ylim(low, high)
        if keep_fixed:
            ax.autoscale(enable=False, axis='y')  # freeze it
    
    fig.tight_layout()
    plt.show()

def multiplot_throughput(dfs, titles, log=True, y_min=None, y_max=None, keep_fixed=True, nrows=2, ncols=3, figsize=(15,8), save_path=None):
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize)
    # Flatten axes so we can index easily; if there's only one row or one column, ensure it's still iterable
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for idx, df in enumerate(dfs):
        ax = axes[idx]
        # Plot each 'burst' group on this Axes
        for burst, group in df.groupby('burst'):
            group_sorted = group.sort_values('queue_size')
            ax.plot(
                group_sorted['queue_size'],
                group_sorted['rx_rate_mbps'],
                marker='o',
                label=f"Burst {burst}"
            )

        ax.set_xlabel('Queue Size (BDP)')
        ax.set_ylabel('Estimated Rate (Mbps)')
        ax.set_title(titles[idx])
        if log:
            ax.set_xscale('log')
        ax.grid(True, which='both', linestyle='--')
        ax.legend()

        # If y‐limits are specified, fix them
        if (y_min is not None) or (y_max is not None):
            cur_low, cur_high = ax.get_ylim()
            low  = cur_low  if y_min is None else y_min
            high = cur_high if y_max is None else y_max
            ax.set_ylim(low, high)
            if keep_fixed:
                ax.autoscale(enable=False, axis='y')

    # Turn off any unused subplots
    for j in range(len(dfs), len(axes)):
        axes[j].axis('off')
        
    # Let tight_layout do its best…
    fig.tight_layout()

    # …but force a little extra vertical padding
    fig.subplots_adjust(hspace=0.35)  # ← increase 'hspace' to push rows apart

        
    # If save_path is provided, write the figure to disk before showing
    if save_path is not None:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")

    fig.tight_layout()
    plt.show()
    
def multiplot_estimated_rate(dfs, titles, log=True, y_min=None, y_max=None, keep_fixed=True, nrows=2, ncols=3, figsize=(15,8), save_path=None):
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize)
    # Flatten axes so we can index easily; if there's only one row or one column, ensure it's still iterable
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for idx, df in enumerate(dfs):
        ax = axes[idx]
        # Plot each 'burst' group on this Axes
        for burst, group in df.groupby('burst'):
            group_sorted = group.sort_values('queue_size')
            ax.plot(
                group_sorted['queue_size'],
                group_sorted['rate_mbps'],
                marker='o',
                label=f"Burst {burst}"
            )

        ax.set_xlabel('Queue Size (BDP)')
        ax.set_ylabel('Estimated Rate (Mbps)')
        ax.set_title(titles[idx])
        if log:
            ax.set_xscale('log')
        ax.grid(True, which='both', linestyle='--')
        ax.legend()

        # If y‐limits are specified, fix them
        if (y_min is not None) or (y_max is not None):
            cur_low, cur_high = ax.get_ylim()
            low  = cur_low  if y_min is None else y_min
            high = cur_high if y_max is None else y_max
            ax.set_ylim(low, high)
            if keep_fixed:
                ax.autoscale(enable=False, axis='y')

    # Turn off any unused subplots
    for j in range(len(dfs), len(axes)):
        axes[j].axis('off')
        
    # Let tight_layout do its best…
    fig.tight_layout()

    # …but force a little extra vertical padding
    fig.subplots_adjust(hspace=0.35)  # ← increase 'hspace' to push rows apart

        
    # If save_path is provided, write the figure to disk before showing
    if save_path is not None:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")

    fig.tight_layout()
    plt.show()
