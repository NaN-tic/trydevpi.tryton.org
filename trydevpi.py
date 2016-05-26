import os
from flask import Flask, render_template
from flask.ext.cache import Cache
from mercurial import ui, hg

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.config.from_envvar('TRYDEVPI_SETTINGS', silent=True)
USERNAME = app.config.get('BB_USERNAME', 'trytonspain')
PREFIX = app.config.get('PREFIX', 'trytonspain')
BASE_URL = 'hg+https://bitbucket.org/%s/' % (USERNAME)


def get_urls(branch_filter=None):
    urls = {}
    lui = ui.ui()
    new_packages = []
    last_series = None
    root_path = app.config.get('HG_PATH', '.')
    for dirname in os.listdir(root_path):
        name = get_module_name(dirname)
        package = get_package(name)
        path = os.path.join(root_path, dirname)
        repo = hg.repository(lui, path)
        last_major = {}
        max_version = (-1, -1)
        for version in repo.tags():
            try:
                major, minor, bug = map(int, version.split('.'))
            except ValueError:
                continue
            key = (major, minor)
            if max_version < key:
                max_version = key
            if last_major.get(key, -1) < bug:
                last_major[key] = bug
        for branch in repo.branchmap().keys():
            if (not repo.branchheads(branch)
                    or (branch_filter and branch != branch_filter)):
                continue
            try:
                major, minor = map(int, branch.split('.'))
            except ValueError:
                continue
            key = (major, minor)
            if max_version < key:
                max_version = key
        if max_version == (-1, -1) and not branch_filter:
            new_packages.append(package)
            continue
        # If default repository we must increase the last tagged version
        if not branch_filter:
            max_version = max_version[0], max_version[1] + 1
        last_major[max_version[0], max_version[1]] = -1
        for (major, minor), bug in last_major.iteritems():
            bug += 1
            version = get_version(major, minor, bug)
            last_series = max(last_series, (major, minor, bug))
            branch = get_branch(major, minor)
            if (not repo.branchheads(branch)
                    or (branch_filter and branch != branch_filter)):
                continue
            url = get_url(package, branch, version, dirname)
            urls['%s-%s' % (package, version)] = url
    for package in new_packages:
        version = get_version(*last_series)
        branch = get_branch(*last_series[:2])
        url = get_url(package, branch, version)
        urls['%s-%s' % (package, version)] = url
    return urls


def get_module_name(name):
    if 'trytond-' in name:
        name = name[len('trytond-'):]
    return name


def get_package(name):
    return '%s_%s' % (PREFIX, name)


def get_version(major, minor, bug):
    template = '%(major)s.%(minor)s.%(bug)s.dev0'
    if minor % 2:
        template = '%(major)s.%(minor)s.dev0'
    return template % {
        'major': major,
        'minor': minor,
        'bug': bug,
        }


def get_branch(major, minor):
    if minor % 2:
        return 'default'
    else:
        return '%s.%s' % (major, minor)


def get_url(name, branch, version, reponame=None):
    url = BASE_URL + (reponame if reponame else name)
    return '%(url)s@%(branch)s#egg=%(name)s-%(version)s' % {
        'url': url,
        'name': name,
        'branch': branch,
        'version': version,
        }


@app.route('/')
@app.route('/<branch>')
@cache.cached(timeout=2 * 60 * 60)
def index(branch=None):
    return render_template('index.html', urls=get_urls(branch))


if __name__ == '__main__':
    app.run(debug=True)
