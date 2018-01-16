from tafor.utils.check import CheckTAF, Listen, remote_message, call_service, call_up
from tafor.utils.validator import Validator, Grammar, Pattern, Parser


def check_upgrade(release_url, current_version, callback=None):
    def get_version_num(version):
        version = version.replace('v', '')
        if 'beta' in version:
            version, beta_num = version.split('-beta')
        else:
            beta_num = None

        nums = version.split('.')
        stable_num = 0
        multiple = 100

        for n in nums:
            stable_num += int(n) * multiple
            multiple = multiple / 10

        return {
            'stable': stable_num,
            'beta':  beta_num
        }

    def version_detect(data):
        release_version = data['tag_name']
        current = get_version_num(current_version)
        release = get_version_num(release_version)
        has_new_version = False

        if release['stable'] > current['stable']:
            has_new_version = True

        if release['stable'] == current['stable']:
            if release['beta'] is None and current['beta']:
                has_new_version = True

            if release['beta'] > current['beta']:
                has_new_version = True

        if callback:
            callback(data, has_new_version)


    try:
        resp = requests.get(release_url, timeout=5)
        data = resp.json()
        version_detect(data)
    except Exception as e:
        pass

# check_upgrade('https://api.github.com/repos/up1and/tafor/releases/latest', __version__)