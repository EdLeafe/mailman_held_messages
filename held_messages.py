import os
import requests
import toml

from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.table import Table


def _parse_creds():
    fpath = os.path.expanduser("~/.mailman_creds.toml")
    return toml.load(fpath)


class HeldMessageProcessor:
    def __init__(self):
        creds = _parse_creds()
        defaults = creds.get("defaults")
        self.host = defaults.get("host")
        self.mail_lists = creds.get("mail_lists")
        self.user_agent = f"held_message_proc-{creds.get('agent', 'standard')}"
        self.data = None
        self.cookies = None
        self.subjects = None

    def get_headers(self, headers=None):
        headers = headers or {}
        default_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-us",
            "Host": self.host,
            "User-Agent": self.user_agent,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        default_headers.update(headers)
        return default_headers

    def delete_messages(self, list_name):
        url = f"https://{self.host}/mailman/admindb/{list_name}"
        headers = self.get_headers()
        resp = requests.post(url, headers=headers, data=self.data, cookies=self.cookies)
        return resp

    def process(self):
        for mail_list in self.mail_lists:
            url = f"https://{self.host}/mailman/admindb/{mail_list}?adminpw={self.mail_lists[mail_list]}"
            response = requests.request("GET", url, headers={}, data={})
            self.cookies = response.cookies
            soup = BeautifulSoup(response.text, features="html.parser")

            self.data = {}
            self.subjects = []
            subject = sender = msg_id = None
            in_subject = False
            cells = soup.find_all("td")

            for cell in cells:
                txt = cell.text
                if in_subject:
                    subject = txt
                in_subject = cell.text == "Subject:"
                contents = cell.contents
                if contents and contents[0].name == "input":
                    atts = contents[0].attrs
                    if not atts["type"] == "hidden":
                        continue
                    sender = atts["name"].replace("%40", "@")
                    msg_id = atts["value"]
                    # Add the data
                    self.data[f"senderaction-{sender}"] = "3"
                    self.data[f"senderforwardto-{sender}"] = f"{mail_list}-owner@leafe.com"
                    self.data[f"senderfilter-{sender}"] = "3"
                    self.data[f"{sender}"] = msg_id
                    # Add to the subjects list
                    self.subjects.append((subject, sender, msg_id))
                    subject = sender = msg_id = None
            self.display_output(mail_list)

    def display_output(self, mail_list):
        subject_count = len(self.subjects)
        if not subject_count:
            print(f"No held messages for {mail_list}.")
            return

        print()
        table = Table(
            title=f"{subject_count} message{'s' if subject_count > 1 else ''} for {mail_list}",
            title_style="bold blue",
            title_justify="left",
            show_header=True,
            box=box.ROUNDED,
            header_style="bold green",
        )
        table.add_column("Subject")
        table.add_column("Sender")
        table.add_column("Message ID")

        self.subjects.sort()
        for subj in self.subjects:
            table.add_row(*subj)
        Console(emoji=True).print(table, overflow="fold")

        should_delete = input(f"Delete th{'ese' if subject_count > 1 else 'is'}? [y]/n ") or "y"
        if should_delete.lower()[0] in "yt":
            self.delete_messages(mail_list)


def main():
    processor = HeldMessageProcessor()
    processor.process()


if __name__ == "__main__":
    main()
