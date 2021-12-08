import asyncio
import os

import aiohttp
from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.table import Table
import toml


def _parse_creds():
    fpath = os.path.expanduser("~/.mailman_creds.toml")
    return toml.load(fpath)


class HeldMessageProcessor:
    def __init__(self, creds, list_name, list_pw):
        self.list_name = list_name
        self.list_pw = list_pw
        defaults = creds.get("defaults")
        self.host = defaults.get("host")
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

    async def delete_messages(self):
        url = f"https://{self.host}/mailman/admindb/{self.list_name}"
        headers = self.get_headers()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, data=self.data, cookies=self.cookies
            ) as resp:
                try:
                    await resp.text()
                except UnicodeDecodeError:
                    pass
            return resp

    async def query_list(self):
        url = f"https://{self.host}/mailman/admindb/{self.list_name}?adminpw={self.list_pw}"
        #         print(f"Querying {self.list_name}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={}, data={}) as resp:
                self.cookies = resp.cookies
                try:
                    text = await resp.text()
                except UnicodeDecodeError:
                    text = await resp.read()
                soup = BeautifulSoup(text, features="html.parser")
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
                self.data[f"senderforwardto-{sender}"] = f"{self.list_name}-owner@leafe.com"
                self.data[f"senderfilter-{sender}"] = "3"
                self.data[f"{sender}"] = msg_id
                # Add to the subjects list
                self.subjects.append((subject, sender, msg_id))
                subject = sender = msg_id = None
        await self.display_output()

    async def display_output(self):
        subject_count = len(self.subjects)
        if not subject_count:
            print(f"No held messages for {self.list_name}.")
            return

        print()
        table = Table(
            title=f"{subject_count} message{'s' if subject_count > 1 else ''} for {self.list_name}",
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
            await self.delete_messages()


async def main():
    creds = _parse_creds()
    mail_lists = creds.get("mail_lists")
    tasks = []
    for list_name, list_pw in mail_lists.items():
        processor = HeldMessageProcessor(creds, list_name, list_pw)
        tasks.append(asyncio.create_task(processor.query_list()))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
