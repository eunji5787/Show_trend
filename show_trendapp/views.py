# -*- coding: utf-8 -*-

from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from show_trendapp.forms import *
from show_trendapp.models import *
from django.db.models import *
from django.template import Context, loader, RequestContext
from django.template.loader import get_template
from django.contrib import messages
import os
import collections
import operator
import datetime
import time
import sys
import urllib2
import re

def home(request):
    obj, trend_date, hour = get_trend_info(request)
    chart_info = chart_trendingurl(obj, trend_date, hour)
    variables = RequestContext(request, chart_info)
    return render_to_response('home.html',locals(), variables)

def get_choices(target_id):
    if target_id >= 0:
        return UrlPerAge.objects.filter(age_date__range=WeekForm().fields['weekdate_choice'].choices_dict[target_id])
    else:
        return []

def get_agechart_info_week(target_id, lastweek_id=None):
    target_list = get_choices(target_id)
    if lastweek_id != None:
        lastweek_list = get_choices(lastweek_id)
        return chart_diff_per_week(target_list, lastweek_list)
    return chart_rank_per_week(target_list)

def make_rank(rank_list):
    rank_dict = {}

    for i in rank_list:
        ind = (i.age_url, i.age_title)
        if ind in rank_dict.keys():
            rank_dict[ind] += i.age_url_cnt
        else:
            rank_dict[ind] = i.age_url_cnt

    ranks = rank_dict.items()
    ranks.sort(key=lambda x: x[1], reverse=True)

    return ranks

def make_diff(target_list, compare_list):
    target_dict = make_rank(target_list)
    compare_dict = dict(make_rank(compare_list))
    same_dict = {}
    diff_dict = {}

    for ind, cnt in target_dict:
        if ind in compare_dict.keys():
            compare_cnt = compare_dict[ind]
            same_dict[ind] = (compare_cnt, cnt, cnt - compare_cnt, compare_cnt + cnt)
        else:
            diff_dict[ind] = (0, cnt, cnt, cnt)

    same_dict = same_dict.items()
    same_dict.sort(key=lambda x: x[1][2], reverse=True)

    diff_dict = diff_dict.items()
    diff_dict.sort(key=lambda x: x[1][3], reverse=True)

    return diff_dict, same_dict

def rank_per_week(request):
    if request.method == 'POST':
        form = WeekForm(request.POST)
        if form.is_valid():
            target_id = int(form.cleaned_data['weekdate_choice'])
    else:
        form = WeekForm()
        target_id = int(form.initial_value()[0])

    chart_info = get_agechart_info_week(target_id)
    variables = RequestContext(request,chart_info)
    return render_to_response('rank_per_week.html',locals(), variables)

def chart_rank_per_week(target_list):
    limit = 30
    weekrank_dict = make_rank(target_list)[:limit]
    xdata, ydata = get_age_x_and_y(weekrank_dict)[:2]
    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartcontainer = 'discretebarchart_container'
    chartdata = {
        'x': xdata, 'y1': ydata, 'extra1': extra_serie,
    }
    charttype = "discreteBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer':chartcontainer,
            }

    return locals()

def diff_per_week(request):
    if request.method == 'POST':
        form = WeekForm(request.POST)
        if form.is_valid():
            target_id = int(form.cleaned_data['weekdate_choice'])
    else:
        form = WeekForm()
        target_id = int(form.initial_value()[0])

    lastweek_id = target_id-1
    chart_info = get_agechart_info_week(target_id, lastweek_id)
    variables = RequestContext(request,chart_info)
    return render_to_response('diff_per_week.html',locals(), variables)

def chart_diff_per_week(target_list, lastweek_list):
    limit = 10
    diff_dict, same_dict = make_diff(target_list, lastweek_list)
    xdata , ydata, ydata1 = get_age_x_and_y(same_dict)
    minus_dict = same_dict[len(same_dict)-limit:len(same_dict)][::-1]
    same_dict = same_dict[:limit]
    diff_dict = diff_dict[:limit]
    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartcontainer = "multibarchart_container"

    chartdata = {
        'x': xdata[:limit],
        'name1': '그 전 주 공유 횟수    '.decode("utf-8"), 'y1': ydata[:limit], 'extra1': extra_serie,
        'name2': '선택한 주 공유 홋수    '.decode("utf-8"), 'y2': ydata1[:limit], 'extra2': extra_serie,
    }
    charttype = "multiBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer':chartcontainer,
            }

    return locals()

def get_agechart_info(target_date, yester_date = None):
    target_list = UrlPerAge.objects.filter(age_date = target_date).order_by('-age_url_cnt')
    if yester_date != None:
        yester_list = UrlPerAge.objects.filter(age_date = yester_date).order_by('-age_url_cnt')
        return chart_diff_per_day(target_list, yester_list)

    return chart_rank_per_day(target_list)

def get_age_x_and_y(dayrank_dict):
    xdata = []
    ydata = []
    ydata1 = []

    for k,v in dayrank_dict:
        xdata.append(k[0])
        if type(v)==tuple:
            ydata.append(v[0])
            ydata1.append(v[1])
        else:
            ydata.append(v)

    return xdata, ydata, ydata1

def rank_per_day(request):
    if request.method == 'POST':
        form = RankPerDayForm(request.POST)
        if form.is_valid():
            target_date = form.cleaned_data['dayrank_date']
    else:
        form = RankPerDayForm()
        target_date = datetime.date.today() - datetime.timedelta(days=1)

    chart_info = get_agechart_info(target_date)
    variables = RequestContext(request,chart_info)
    return render_to_response('rank_per_day.html',locals(), variables)

def chart_rank_per_day(dayrank_list):
    limit = 30
    dayrank_dict = make_rank(dayrank_list)[:limit]
    xdata, ydata = get_age_x_and_y(dayrank_dict)[:2]
    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartcontainer = 'discretebarchart_container'
    charttype = "discreteBarChart"

    chartdata = {
        'x': xdata,
        'y1': ydata,
        'extra1': extra_serie,
    }

    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
    }

    return locals()

def diff_per_day(request):
    if request.method == 'POST':
        form = DiffPerDayForm(request.POST)
        if form.is_valid():
            target_date = form.cleaned_data['daydiff_date']
    else:
        form = DiffPerDayForm()
        target_date = datetime.date.today() - datetime.timedelta(days=1)

    yester_date = target_date - datetime.timedelta(days=1)
    chart_info = get_agechart_info(target_date, yester_date)
    variables = RequestContext(request,chart_info)
    return render_to_response('diff_per_day.html',locals(), variables)

def chart_diff_per_day(target_list, yester_list):
    limit = 10
    diff_dict, same_dict = make_diff(target_list, yester_list)
    xdata , ydata, ydata1 = get_age_x_and_y(same_dict)
    minus_dict = same_dict[len(same_dict)-limit:len(same_dict)][::-1]
    same_dict = same_dict[:limit]
    diff_dict = diff_dict[:limit]
    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartcontainer = "multibarchart_container"

    chartdata = {
        'x': xdata[:limit],
        'name1': '어제 공유 횟수    '.decode("utf-8"), 'y1': ydata[:limit], 'extra1': extra_serie,
        'name2': '오늘 공유 홋수    '.decode("utf-8"), 'y2': ydata1[:limit], 'extra2': extra_serie,
    }
    charttype = "multiBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer':chartcontainer,
            }

    return locals()

def get_trafficday_chart_info(start_time, end_time):
    traffic_cnt_list = TrafficPerHour.objects.filter(
        traffic_date__range = [start_time, end_time]
        ).values('traffic_date').annotate(Sum('traffic_cnt'))

    return chart_traffic_per_day(start_time, end_time, traffic_cnt_list)

def traffic_per_day(request):
    show_week = True
    if request.method == 'POST':
        form = TrafficPerDayForm(request.POST)
        if form.is_valid():
            show_week = False
            start_time = form.cleaned_data['traffic_start']
            end_time = form.cleaned_data['traffic_end']
    else:
        form = TrafficPerDayForm()
        end_time = datetime.date.today() - datetime.timedelta(days=1)
        start_time = end_time - datetime.timedelta(days=6)

    chart_info = get_trafficday_chart_info(start_time, end_time)
    variables = RequestContext(request, chart_info)
    return render_to_response('traffic_per_day.html',locals(), variables)

def chart_traffic_per_day(start_time, end_time, traffic_cnt_list):
    ydata = [0]*int(((end_time-start_time).days)+1)
    time_info = [start_time + datetime.timedelta(days=x) for x in range(len(ydata))]

    for i in traffic_cnt_list:
        traffic_time = i['traffic_date']
        if traffic_time in time_info:
            ydata[time_info.index(traffic_time)] = i['traffic_cnt__sum']

    xdata = map(lambda x: int(time.mktime(x.timetuple()))*1000, time_info)
    scrap_counts_diff = calculate_difference(ydata)

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    charttype = "lineChart"
    extra_serie = { "tooltip": {"y_start": "", "y_end": " cal"}, "date_format": tooltip_date }
    kw_extra = { 'x_is_date': True , 'x_axis_format': "%d %b %Y" }
    chartdata = {
        'x': xdata, 'name': '일별 스크랩 횟수'.decode("utf-8"), 'y': ydata, 'extra':extra_serie }
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'kw_extra' : kw_extra,
        }

    return locals()

def get_traffichour_chart_info(target_date):
    traffic_cnt_list = TrafficPerHour.objects.filter(traffic_date = target_date).order_by('traffic_hh')

    return chart_traffic_per_hour(traffic_cnt_list)

def traffic_per_hour(request):
    show_today = True

    if request.method == 'POST':
        form = TrafficPerHourForm(request.POST)
        if form.is_valid():
            show_today = False
            target_date = form.cleaned_data['traffic_date']
    else:
        form = TrafficPerHourForm()
        target_date = datetime.date.today() - datetime.timedelta(days=1)

    chart_info = get_traffichour_chart_info(target_date)
    variables = RequestContext(request, chart_info)
    return render_to_response('traffic_per_hour.html',locals(), variables)

def chart_traffic_per_hour(traffic_cnt_list):
    xdata = []
    ydata = []

    for i in traffic_cnt_list:
        xdata.append(i.traffic_hh)
        ydata.append(i.traffic_cnt)

    scrap_counts_diff = calculate_difference(ydata)

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"}, "date_format": tooltip_date}
    chartdata = {
        'x': xdata, 'name': '시간별 스크랩 횟수'.decode("utf-8"), 'y': ydata, 'extra': extra_serie }
    kw_extra = { 'x_is_date': False , 'x_axis_format': ""}
    charttype = "lineChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'kw_extra' : kw_extra
    }

    return locals()

def calculate_difference(scrap_counts):
    l = [0]
    for i in range(1, len(scrap_counts)):
        diff = scrap_counts[i] - scrap_counts[i -1]
        l.append(diff)

    return l

def get_twentyfive_x_and_y(age_list):
    time_info = []
    ydata = []
    xdata = []

    for i in age_list:
        if not i.age_url in xdata:
            xdata.append(i.age_url)
            ydata.append(i.age_url_cnt)
            time_info.append(i.age_date)

    return xdata, ydata, time_info

def get_twentyfive_chart_info(start_time, end_time):
    undertf_list = UrlPerAge.objects.filter(age_date__range = [start_time, end_time], over_tf=False
        ).order_by('-age_url_cnt')
    overtf_list = UrlPerAge.objects.filter(age_date__range = [start_time, end_time], over_tf=True
        ).order_by('-age_url_cnt')

    return chart_twentyfive_trend(undertf_list, overtf_list)

def twentyfive_trend(request):
    show_week = True

    if request.method == 'POST':
        form = UrlPerAgeForm(request.POST)
        if form.is_valid():
            show_week = False
            start_time = form.cleaned_data['age_start']
            end_time = form.cleaned_data['age_end']
    else:
        form = UrlPerAgeForm()
        end_time = datetime.date.today() - datetime.timedelta(days=1)
        start_time = end_time - datetime.timedelta(days=6)

    chart_info = get_twentyfive_chart_info(start_time, end_time)
    variables = RequestContext(request, chart_info)
    return render_to_response('twentyfive_trend.html', locals(), variables)

def chart_twentyfive_trend(undertf_list, overtf_list):
    xdata1, ydata1, time_info1 = get_twentyfive_x_and_y(undertf_list)
    xdata2, ydata2, time_info2 = get_twentyfive_x_and_y(overtf_list)
    extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"}}
    chartcontainer = 'discretebarchart_container'
    chartcontainer1 = 'discretebarchart_container1'

    limit = 10
    chartdata = { #25세 이하
        'x': xdata1[:limit], 'y1': ydata1[:limit], 'extra1': extra_serie,
    }
    chartdata1 = { #25세 이상
        'x': xdata2[:limit], 'y1': ydata2[:limit], 'extra1': extra_serie,
    }
    charttype = "discreteBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartdata1': chartdata1,
        'chartcontainer':chartcontainer,
        'chartcontainer1': chartcontainer1
            }

    return locals()

def get_trend_info(request, form=None):
    limit = 10
    latest = TrendingUrl.objects.order_by('-trend_date', '-trend_hh')[0]
    trend_date, hour = latest.trend_date, latest.trend_hh
    if request.method == 'POST':
        if request.POST.has_key('hour'):
            hour = request.POST.get('hour')
        if request.POST.has_key('manage'):
            hour, selected_url = request.POST.get('manage').split("/",1)
            select_url(selected_url)

        if form.is_valid():
            trend_date = form.cleaned_data['trend_date']
            hour = int(hour)
            if not TrendingUrl.objects.filter(trend_date = trend_date, trend_hh = hour).exists():
                return [], trend_date, hour

    return TrendingUrl.objects.filter(trend_date = trend_date, trend_hh = hour).order_by('-trend_url_cnt')[:limit], trend_date, hour

def hourly_trending_url(request):
    if request.method == 'POST':
        form = TrendingUrlForm(request.POST)
    else:
        form = TrendingUrlForm()

    obj, trend_date, hour = get_trend_info(request, form)
    chart_info = chart_trendingurl(obj, trend_date, hour)
    variables = RequestContext(request, chart_info)
    return render_to_response('hourly_trending_url.html',locals(), variables)

def chart_trendingurl(trending_list, trend_date, hour):
    title = []
    xdata = []
    ydata = []

    for i in trending_list:
        xdata.append(i.trend_url)
        ydata.append(i.trend_url_cnt)
        title.append(i.trend_title)


    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartdata = {'x': xdata, 'y1': ydata, 'extra1': extra_serie}
    charttype = "discreteBarChart"
    data = {'charttype': charttype, 'chartdata': chartdata }

    return locals()

def manageurl_form(request):
    trend_url = ManageUrlForm().initial_value()[0]
    if request.method == 'POST':

        if request.POST.has_key('delete'):
            deleted_url = request.POST.get('delete')
            if len(deleted_url) == 0:
                deleted_url = request.POST.get('trend_url')
            form = delete_url(deleted_url)

        elif request.POST.has_key('select'):
            form = ManageUrlForm(request.POST)
        if form.is_valid():
            trend_url = form.cleaned_data['trend_url']
    else:
        form = ManageUrlForm()

    return trend_url, form

def manage_url(request):
    trend_url, form = manageurl_form(request)
    chart_info = chart_manage_url(trend_url)
    variables = RequestContext(request, chart_info)
    return render_to_response('manage_url.html', locals(),variables)

def chart_manage_url(trend_url):
    try:
        url_list = TrendingUrl.objects.filter(trend_url=trend_url)
        start_date , start_hour = url_list.earliest('trend_date').trend_date , url_list.earliest('trend_date').trend_hh
        end_date, end_hour =  url_list.latest('trend_date').trend_date, url_list.latest('trend_date').trend_hh
        time_list = [i.trend_hh for i in url_list]
        time_set =  set([(x,time_list.count(x)) for x in time_list])

        xdata = [i for i in range(24)]
        ydata1 = [0]*len(xdata)
        ydata2 = [0]*len(xdata)
        cntperhour = [0]*len(xdata)

        for i in url_list:
            ind = xdata.index(i.trend_hh)
            if ydata1[ind] == 0:
                ydata1[ind] = i.trend_url_cnt
            else:
                ydata1[ind] = ydata1[ind] + i.trend_url_cnt

        for i in time_set:
            ydata2[i[0]] = ydata1[i[0]]/i[1]
            cntperhour[i[0]] = i[1]

    except:
        xdata = []
        ydata1 = []
        ydata2 = []
        cntperhour = []

    finally:
        tooltip_date = "%d %b %Y %H:%M:%S %p"
        extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"},
                       "date_format": tooltip_date}
        chartdata = {
            'x': xdata,
            'name1': '  시간별 누적 스크랩 횟수  ', 'y1': ydata1, 'extra': extra_serie,
            'name2': '  시간별 평균 스크랩 횟수  ', 'y2': ydata2, 'extra': extra_serie,
        }
        kw_extra = { 'x_is_date': False , 'x_axis_format': ""}
        charttype = "lineChart"
        data = {
            'charttype': charttype,
            'chartdata': chartdata,
            'kw_extra' : kw_extra,
        }

    return locals()

def start_and_end(trend_url):
    if trend_url:
        start_date = UrlPerAge.objects.filter(age_url=trend_url).earliest('age_date').age_date
        end_date = UrlPerAge.objects.filter(age_url=trend_url).latest('age_date').age_date
        days = (end_date-start_date).days

    return start_date, end_date, days

def manage_url_day(request):
    trend_url, form = manageurl_form(request)
    chart_info = chart_manage_url_day(trend_url)
    variables = RequestContext(request, chart_info)
    return render_to_response('manage_url_day.html', locals(),variables)

def chart_manage_url_day(trend_url):
    try:
        show_chart = True
        start_date, end_date, days = start_and_end(trend_url)
        url_list = UrlPerAge.objects.filter(age_url=trend_url).values("age_date").annotate(Sum('age_url_cnt'))
        ydata1 = [0]*int(days+1)
        time_info = [start_date + datetime.timedelta(days=x) for x in range(len(ydata1))]
        for i in url_list:
            ind = time_info.index(i['age_date'])
            ydata1[ind] = i['age_url_cnt__sum']
        xdata = map(lambda x: int(time.mktime(x.timetuple()))*1000, time_info)

    except:
        show_chart = False
        ydata1 = []
        xdata = []
        time_info = []

    finally:
        tooltip_date = "%d %b %Y %H:%M:%S %p"
        extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"},
                       "date_format": tooltip_date}
        chartdata = {
            'x': xdata,
            'name1': '  일별 스크랩 횟수  ', 'y1': ydata1, 'extra': extra_serie,
        }
        kw_extra = { 'x_is_date': True , 'x_axis_format': "%d %b %Y" }
        charttype = "lineChart"
        data = {
            'charttype': charttype,
            'chartdata': chartdata,
            'kw_extra' : kw_extra,
        }

        return locals()

def manage_url_week(request):
    trend_url, form = manageurl_form(request)
    chart_info = chart_manage_url_week(trend_url)
    variables = RequestContext(request, chart_info)
    return render_to_response('manage_url_week.html', locals(),variables)

def chart_manage_url_week(trend_url):
    try:
        show_chart = True
        start_date , end_date = start_and_end(trend_url)[:2]
        time_info = map(lambda (k,v): v, WeekForm().fields['weekdate_choice'].choices_dict.items())
        time_info1 = map(lambda (k,v): v, WeekForm().fields['weekdate_choice'].choices)
        url_list = map(get_choices, range(len(time_info)))
        ydata = map(lambda x: x.filter(age_url=trend_url).aggregate(Sum('age_url_cnt'))['age_url_cnt__sum'] ,url_list)
        xdata = map(lambda x: int(time.mktime(x[0].timetuple()))*1000, time_info)

    except:
        show_chart = False
        ydata = []
        xdata = []
        time_info = []

    finally:
        tooltip_date = "%d %b %Y %H:%M:%S %p"
        extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"},
                       "date_format": tooltip_date}
        chartdata = {
            'x': xdata,
            'name1': '  주별 스크랩 횟수  ', 'y1': ydata, 'extra': extra_serie,
        }
        kw_extra = { 'x_is_date': True , 'x_axis_format': "%d %b %Y" }
        charttype = "lineChart"
        data = {
            'charttype': charttype,
            'chartdata': chartdata,
            'kw_extra' : kw_extra,
        }

        return locals()

def select_url(selected_url=None):

    if TrendingUrl.objects.filter(trend_url=selected_url).exists():
        TrendingUrl.objects.filter(trend_url=selected_url).update(manage_url=True)

def delete_url(deleted_url):

    if TrendingUrl.objects.filter(trend_url=deleted_url).exists():
        TrendingUrl.objects.filter(trend_url=deleted_url).update(manage_url=False)

    return ManageUrlForm({'trend_url': '' })

