import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from tqdm import tqdm

def request_web_page(type='3', term='2024-2025-2', config_path=None, serverid=None, JSESSIONID=None, save_path='demo/response.html'):
    """ Request the web page and save it to a file

    Args:
        type (str):         '1' for lectures, '2' for experiments, '3' for all
        term (str):         in the format of 'YYYY-YYYY-S', e.g. '2024-2025-2'
        config_path (str):  path to the configuration file
        serverid (str):     serverid in the cookies
        JSESSIONID (str):   JSESSIONID in the cookies
        save_path (str):    path to save the response
    """
    type_map = {
        '1': ['kb', '%D2%BB%BC%B6%D1%A1%BF%CE%BF%CE%B1%ED'], 
        '2': ['kb', '%B6%FE%BC%B6%D1%A1%BF%CE%BF%CE%B1%ED'], 
        '3': ['ztkb', '%D5%FB%CC%E5%BF%CE%B1%ED']
    }
    url = f'https://zhjwxk.cic.tsinghua.edu.cn/syxk.vsyxkKcapb.do?m={type_map[type][0]}Search&p_xnxq={term}&pathContent={type_map[type][-1]}'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,en-GB;q=0.6',
        'Priority': 'u=0, i',
        'Referer': f'https://zhjwxk.cic.tsinghua.edu.cn/xkBks.vxkBksXkbBs.do?m=showTree&p_xnxq={term}',
        'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
    }
    if serverid is not None and JSESSIONID is not None:
        cookies = {
            'serverid': serverid,
            'JSESSIONID': JSESSIONID,
        }
    elif config_path is not None:
        with open(config_path, 'r') as f:
            config = json.load(f)
            cookies = {
                'serverid': config['serverid'],
                'JSESSIONID': config['JSESSIONID'],
            }
    else:
        cookies = None

    try:
        response = requests.get(url, headers=headers, cookies=cookies)
    except requests.exceptions.RequestException as e:
        print(e)
        return None
    print(f'{response.status_code}: get {len(response.text)} characters in {response.apparent_encoding} encoding')

    encode = response.apparent_encoding
    if encode in ['gbk', 'GB2312', 'GB18030', 'GBK']:
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
    else:
        # wish they will update the encoding in the future
        with open(save_path, 'w') as f:
            f.write(response.text)

    return save_path

def parse_html(html_path, save_path='demo/courses.json'):
    # 'function setInitValue()' in the html stores the data
    raw_data = None
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script')
        spans = soup.find_all('span')
        inputs = soup.find_all('input')

        raw_data = scripts[14].string.split('function setInitValue()')[1].split('Event.observe(window, "load", setInitValue, false);')[0]
        
    courses = []
    prog_bar = tqdm(raw_data.split('<a'), desc='Parsing courses', leave=False)
    for part in prog_bar:
        if '/a>' not in part:
            continue
        course = {}
        if '/a>' not in part.split('\n')[0]:
            course['course_id'] = part.split('target=')[0].split('&p_id=')[1].split(';')[1][:8]
            course['credit'] = int(course['course_id'][-1])
            prog_bar.set_description(f'Identified course {course["course_id"]}')

            count = 0
            flag_PE = False
            for line in part.split('\n'):
                if 'strHTML' not in line:
                    continue
                count += 1
                if count == 1:
                    course['name'] = line.split('\"<b>')[1].split('</b>\"')[0]
                elif count == 3:
                    course['teacher'] = line.split('\"；')[1].split('\"')[0]
                elif count == 4:
                    s = line.split('\"；')[1].split('\"')[0]
                    if '周' in s:
                        course['type'] = '必修'
                        course['weeks'] = s
                        flag_PE = True
                    else:
                        course['type'] = s
                elif count == 5:
                    if flag_PE:
                        course['position'] = line.split('\"；')[1].split('\"')[0]
                        break
                    else:
                        course['weeks'] = line.split('\"；')[1].split('\"')[0]
                elif count == 6:
                    course['position'] = line.split('\"；')[1].split('\"')[0]
                    break
            course['weekday'] = part.split("getElementById(\'a")[1][2]
            course['time'] = part.split("getElementById(\'a")[1][0]
        else:
            course['course_id'] = part.split('target=')[0].split('&p_id=')[1][:8]
            course['credit'] = int(course['course_id'][-1])
            prog_bar.set_description(f'Identified course {course["course_id"]}')

            course['name'], rest = part.split("<b><font color=\'blue\'>")[1].split('</font></b>')
            count = 0
            for item in rest.split('；'):
                count += 1
                if count == 1:
                    course['position'] = item.split('(')[1]
                elif count == 2:
                    course['weeks'] = item
                elif count == 3:
                    course['weekday'] = item.split("getElementById(\'a")[1][2]
                    course['time'] = item.split("getElementById(\'a")[1][0]
                    course['comment'] = item.split('：')[1].split(')</font>')[0]
            course['type'] = '实验'
        courses.append(course)

    schedule = []
    # fill with 7 lists of 6 dictionaries
    for i in range(1, 8):
        day = []
        for j in range(1, 7):
            day.append({'time': f'{i}_{j}'})
        schedule.append(day)
    for course in courses:
        schedule[int(course['weekday']) - 1][int(course['time']) - 1]['course'] = course
        if course['time'] in ['2', '6']:
            # need to know the length of the course
            schedule[int(course['weekday']) - 1][int(course['time']) - 1]['length'] = 3 if course['credit'] > 2 else 2
        else:
            schedule[int(course['weekday']) - 1][int(course['time']) - 1]['length'] = 2

    info = {}
    for item in inputs: 
        if 'p_xnxq' in item.attrs['name']:
            info['term'] = item.attrs['value']
            break
    for span in spans:
        if '学号:' in span.text:
            info['student_id'] = span.text.split('学号:')[1].strip()
        elif '姓名:' in span.text:
            info['name'] = span.text.split('姓名:')[1].strip()
        if len(info) == 3:
            break

    output = {
        'info': info,
        'courses': courses,
        'schedule': schedule
    }
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    return save_path

def build_schedule_html(courses_path, save_path):
    with open(courses_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        schedule = json_data.get('schedule')
        info = json_data.get('info')
    
    start_map = {
        1: 1, 
        2: 3,   # 3 class hours
        3: 6, 
        4: 8, 
        5: 10, 
        6: 12,  # 3 class hours
        7: 15
    }
    time_map = {
        1: ['08:00', '09:35'],
        2: ['09:50', '12:15'],
        3: ['13:30', '15:05'],
        4: ['15:20', '16:55'],
        5: ['17:10', '18:45'],
        6: ['19:20', '21:45']
    }

    length_table = {k: [1 for _ in range(7)] for k in range(1, 15)}
    for weekday in range(1, 8):
        for classtime in range(1, 7):
            if 'length' in schedule[weekday - 1][classtime - 1]:
                length = schedule[weekday - 1][classtime - 1]['length']
                length_table[start_map[classtime]][weekday - 1] = length
                for i in range(1, length):
                    length_table[start_map[classtime] + i][weekday - 1] = 0

    html = str()

    part = '''
<html>
<head>
    <title>课程表</title>
    <style>
        body {
            font-family: Arial, 微软雅黑, 楷体, 宋体, sans-serif;
            background-color: #f2f2f2;
        }
        h2 {
            margin: 25px 10px 0;
            text-align: center;
        }
        .info {
            margin: 10px auto;
            text-align: center;
        }
        table {
            border-collapse: collapse;
            margin: 10px auto;
        }
        th, td {
            border: 1px solid black;
            padding: 8px;
        }
        th {
            width: 13.5%;
            background-color: #f2f2f2;
            text-align: center;
            font-weight: bold;
        }
        th.first_column {
            width: 5.5%;
        }
        td {
            height: 100px;
            vertical-align: bottom;
            text-align: left;
        }
        td.first_column {
            text-align: center;
            font-size: 1.2em;
            vertical-align: middle;
        }
        td.type_expe {
            background-color: #FCD4D480;
        }
        td.type_elec {
            background-color: #E3FBE380;
        }
        td.type_comp {
            background-color: #DFDFFF80;
        }
        .start_time {
            font-size: 0.8em;
            height: 15%;
            display: flex;
            align-items: flex-start;
            justify-content: flex-end;
        }
        .start_time p {
            text-align: right;
            vertical-align: top;
        }
        .order {
            font-size: 1.5em;
            font-weight: bold;
            font-style: italic;
            height: 70%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .order p {
            vertical-align: middle;
        }
        .end_time {
            font-size: 0.8em;
            height: 15%;
            display: flex;
            align-items: flex-end;
            justify-content: flex-end;
        }
        .end_time p {
            text-align: right;
            vertical-align: bottom;
        }
        p {
            margin: 0;
        }
        p.name {
            font-weight: bold;
            font-size: 1.2em;
            margin: 5px 0;
        }
        @media (prefers-color-scheme: dark) {
            body {
                background-color: #333333;
                color: #ffffff;
            }
            th {
                background-color: #444444;
                color: #ffffff;
            }
            td {
                background-color: #555555;
                color: #ffffff;
            }
            td.type_expe {
                background-color: #FCD4D450;
            }
            td.type_elec {
                background-color: #E3FBE350;
            }
            td.type_comp {
                background-color: #DFDFFF50;
            }
        }
    </style>
</head>
    '''
    html += part

    part = f'''
<body>
    <h2>{info['term'][:9]} 学年{'秋' if info['term'][-1] == '1' else '春'}季学期课程表</h2>
    <div class=info>
        <p>学号：{
            info['student_id']
        }　　姓名：{
            info['name']
        }　　更新时间：{
            datetime.fromtimestamp(os.path.getmtime(courses_path)).strftime('%Y/%m/%d %H:%M:%S')
        }</p>
    <div>
    <table>
        <tr>
            <th class=first_column>节次</th>
            <th><p>周一</p><p>Mon.</p></th>
            <th><p>周二</p><p>Tue.</p></th>
            <th><p>周三</p><p>Wed.</p></th>
            <th><p>周四</p><p>Thu.</p></th>
            <th><p>周五</p><p>Fri.</p></th>
            <th><p>周六</p><p>Sat.</p></th>
            <th><p>周日</p><p>Sun.</p></th>
        </tr>
    '''
    html += part

    for i in range(1, 7):
        part = f'''
        <tr>
            <td class=first_column rowspan={start_map[i + 1] - start_map[i]}>
                <div class=start_time><p>{time_map[i][0]}</p></div>
                <div class=order><p>{i}</p></div>
                <div class=end_time><p>{time_map[i][1]}</p></div>
            </td>
        '''
        html += part

        for j in range(1, 8):
            if length_table[start_map[i]][j - 1] > 1:
                part = f'<td rowspan={length_table[start_map[i]][j - 1]}'
            else:
                part = f'<td'

            if 'course' in schedule[j - 1][i - 1]:
                course = schedule[j - 1][i - 1]['course']

                if 'type' not in course:
                    pass
                elif course['type'] == '实验':
                    part += ' class=type_expe'
                elif course['type'] == '任选':
                    part += ' class=type_elec'
                elif course['type'] == '必修':
                    part += ' class=type_comp'

                part += '>'

                part += f'''
                <p class=name>{course["name"]}</p>
                <p class=teacher>{course["teacher"] if "teacher" in course else course["comment"]}</p>
                <p class=position>{course["position"]}</p>
                <p class=weeks>{course["weeks"]}</p>
                '''
            else:
                part += '>'
            part += '</td>'
            html += part
        
        part = '</tr>'
        html += part

        for j in range(start_map[i] + 1, start_map[i + 1]):
            part = f'''
        <tr>
            '''
            for k in range(1, 8):
                if length_table[j][k - 1] == 0:
                    continue
                else:
                    part += '<td></td>'
            part += '</tr>'
            html += part

    part = '''
    </table>
</body>
</html>
    '''
    html += part

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return save_path

if __name__ == '__main__':
    build_schedule_html(
        parse_html(
            request_web_page(
                type='all',
                term='2024-2025-2',
                config_path='config.json',
                save_path='demo/response.html'
            ),
            'demo/courses.json'
        ),
        'demo/schedule.html'
    )