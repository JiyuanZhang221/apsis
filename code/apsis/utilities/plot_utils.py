__author__ = 'Frederik Diehl'
import matplotlib.pyplot as plt
import random
import os

def plot_lists(to_plot_list, fig=None, fig_options=None, plot_at_least=(1, 1)):
    """
    Plots several functions.

    Each entry of to_plot_list defines x, y, and format options.

    Parameters
    ----------
    to_plot_list: list of dicts
        Defines the functions to plot.
        Each entry must contain at least values for "x" and
        "y", and can contain values for "type", "label" and "color".
        x: list
            A list of x values
        y: list
            A list of y values
        type="line": string
            Either "line", in which case a line will be plotted, or "scatter",
            in which case a scatter plot will be made.
        label="": string
            The label for the function.
        color=random colour: string
            Which color the plot should have.
    fig=None: pyplot.figure
        A plot to continue, or None in which case a new plot is made using
        plot_options.
    fig_options=None: dict
        Options used when creating a new plot.
        "legend_loc"="upper right": string
            Location for the legend.
        "x_label"="": string
            x label for the figure
        "y_label"="": string
            y label for the figure

    Returns
    -------
    fig: plt.figure
        Either a new figure or fig, now containing the plots as specified.
    """
    newly_created = False
    if fig is None:
        fig = _create_figure(fig_options)
        newly_created = True
    for p in to_plot_list:
        fig = plot_single(p, fig)

    if (plot_at_least[0] < 1) or plot_at_least[1] < 1:
        max_y = -float("inf")
        min_y = float("inf")

        for i in range(len(to_plot_list)):
            cur_min, cur_max = _get_y_min_max(to_plot_list[i]["y"], plot_at_least)
            if cur_min < min_y:
                min_y = cur_min
            if cur_max > max_y:
                max_y = cur_max
            plt.ylim(ymax = max_y, ymin = min_y)

    if newly_created:
        _polish_figure(fig, fig_options)

    return fig

def _get_y_min_max(y, plot_at_least):
    sorted_y = sorted(y)
    max_y_new = sorted_y[min(len(sorted_y)-1, int(plot_at_least[1] * len(sorted_y)))]
    min_y_new = sorted_y[int(plot_at_least[0] * (1-len(sorted_y)))]
    return min_y_new, max_y_new

COLORS = ["g", "r", "c", "b", "m", "y"]


def plot_single(to_plot, fig=None, fig_options=None):
    """
    Plots a single function.

    to_plot defines x, y, and format options.

    Parameters
    ----------
    to_plot: dict
        Defines the function to plot. Must contain at least values for "x" and
        "y", and can contain values for "type", "label" and "color".
        x: list
            A list of x values
        y: list
            A list of y values
        type="line": string
            Either "line", in which case a line will be plotted, or "scatter",
            in which case a scatter plot will be made.
        label="": string
            The label for the function.
        color=random colour: string
            Which color the plot should have.
    fig=None: pyplot.figure
        A plot to continue, or None in which case a new plot is made using
        fig_options.
    fig_options=None: dict
        Options used when creating a new plot.
        "legend_loc"="upper right": string
            Location for the legend.
        "x_label"="": string
            x label for the figure
        "y_label"="": string
            y label for the figure

    Returns
    -------
    fig: plt.figure
        Either a new figure or fig, now containing the plots as specified.
    """
    newly_created = False
    if fig is None:
        fig = _create_figure(fig_options)
        newly_created = True
    plt.figure(fig.number)
    type = to_plot.get("type", "line")
    label = to_plot.get("label", "")
    color = to_plot.get("color", random.choice(COLORS))
    x = to_plot.get("x", [])
    y = to_plot.get("y", [])

    if type == "line":
        plt.plot(x, y, label=label, color=color)
    elif type=="scatter":
        plt.scatter(x, y, label=label, color=color)

    if newly_created:
        _polish_figure(fig_options)
    return fig

def write_plot_to_file(fig, filename, store_path,  file_format="png", transparent=False):
    """
    Wirte out plot to the file given in filename. Assumes that all
    directories already exist.

    Parameters
    ----------
    fig: matplotlib.figure
        The figure object to store.
    filename: string or os.path
        A string or path can be given here to specify where
        the plot is written to. All parent directories have to exist!
    file_format="png": string
        Specifies file format of plot - all supported file formats
        by matplotlib can be given here.
    transparent=False: boolean
        Specifies if a transparent figure is written
    """
    filename_w_extension = os.path.join(store_path, filename + "." + file_format)
    fig.savefig(filename_w_extension, format=file_format, transparent=transparent)

    plt.close(fig)

def _create_figure(fig_options=None):
    """
    Creates a new figure with fig_options.

    Parameters
    ----------
    fig_options=None: dict
        Options used when creating a new plot.
        "x_label"="": string
            x label for the figure
        "y_label"="": string
            y label for the figure
        "title"="": string
            The title for the figure.

    Returns
    -------
    fig: plt.figure
        A new figure with the options as specified in fig_options.
    """
    if fig_options is None:
        fig_options = {}
    fig = plt.figure()
    plt.xlabel(fig_options.get("x_label", ""))
    plt.ylabel(fig_options.get("y_label", ""))
    plt.title(fig_options.get("title", ""))
    return fig

def _polish_figure(fig, fig_options=None):
    """
    Polishes a finished figure.

    fig_options=None: dict
        Options used.
        "legend_loc"="upper right": string
            Location for the legend.
    """
    plt.figure(fig.number)
    if fig_options is None:
        fig_options = {}

    legend_loc = fig_options.get("legend_loc", "below")


    if legend_loc == "below":
        #TODO This code doesn't work yet, needs to be fixed - but before
        # matplotlib usage has to be refactored to use pure object
        #oriented mode.

        # Shrink current axis's height by 10% on the bottom
        box = fig.get_position()
        fig.set_position([box.x0, box.y0 + box.height * 0.1,
                 box.width, box.height * 0.9])

        # Put a legend below current axis
        fig.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
          fancybox=True, shadow=True, ncol=5)
    elif legend_loc == "no":
        #do nothing right now, since no legend
        pass
    else:
        plt.legend(loc=legend_loc)


