# mailman_held_messages
A quick way to process held Mailman v2 messages.

Note that you can either delete all the held messages for the list, or save them all. There is no
capability (yet!) to mark individual messages to be held or deleted.

To configure you'll need to create a file named `.mailman_creds.toml` in your home directory. This
should be a typical **TOML** file, with two sections: 'defaults' and 'mail_lists'. Here is a sample: 

```
[defaults]
host = "example.com"

[mail_lists]
test_list = "topsecret"
birds = "foobar"
weather = "toomuchrain"

```

The `host` should be the host where your Mailman service is running. In the `mail_lists` section,
add a line for each list that you host. The format for each line is: `<list_name> =
"<list_admin_password>"`.

Since this project is managed by [poetry](https://python-poetry.org/docs/ "poetry"), you should have
poetry installed on your machine. Run `poetry install` to install the dependencies before running
the script. You only have to do this once.

Once the dependencies are installed, call `poetry run python held_messages.py` to run the script,
which will process each of your lists sequentially. If there are held messages for any of your
lists, you will be shown a list containing the subject, sender, and message ID for each message. If
there are **any** messages that should not be discarded, answer `n` at the prompt, and the messages
will not be touched. But if they are all spam, answer `y` and press Enter, and the messages will be
discarded.
