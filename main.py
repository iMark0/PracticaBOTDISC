import argparse
import re
import asyncio

import toml
from discord import Member, User, Message, Guild, Reaction
from discord.ext import commands
from discord.ext.commands import Context, Bot

EMOJI_CHECK_MARK = '✔️'
EMOJI_CROSS_MARK = '❌'

AWAITING_GROUP, AWAITING_NICKNAME_CHANGE = range(2)


def valid_nickname(member: Member) -> bool:

    return member.nick and re.match(r'^\w+ \w+$', member.nick) is not None


class Greeter(commands.Cog):
    def __init__(self, bot: Bot, admin_id: int, guild_id: int):
        self.bot = bot
        self.admin_id = int(admin_id)
        self.guild_id = int(guild_id)
        self.awaiting_approval = dict()

    async def get_guild(self) -> Guild:
        guild = self.bot.get_guild(self.guild_id)
        if guild is not None:
            return guild
        guild = await self.bot.fetch_guild(self.guild_id)
        if guild is None:
            print('MAYDAY: Cog has invalid guild id')
            exit(1)
        return guild

    async def get_admin(self) -> User:
        admin = self.bot.get_user(self.admin_id)
        if admin is not None:
            return admin
        admin = await self.bot.fetch_user(self.admin_id)
        if admin is None:
            print('MAYDAY: Cog has invalid admin id')
            exit(1)
        return admin

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        pass

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        print(f'New member joined: {member.display_name}')
        await member.send('Greetings stranger! I am guardian of this petty server you just joined. '
                          'Welcome to the our glorious university server!\n'
                          'First things first, what is your name? '
                          'Please, set your nickname (right click yourself in server members list, then click nickname) '
                          'to your real name in format\n'
                          '`<first name> <second Name>`\n'
                          'Once this is done, use command\n'
                          '`!role <your group>\n`'
                          'To join relevant group. If you are a staff member, use\n'
                          '`!role staff`')

    @commands.command()
    async def role(self, ctx: Context, group: str = None):
        # answer only DMs
        if isinstance(ctx.author, Member):
            return
        if group is None:
            await ctx.send('Usage: !role <your group>')

        guild = await self.get_guild()
        member = await guild.fetch_member(ctx.author.id)
        if not valid_nickname(member):
            await ctx.send('Please make sure your nickname is in the following format:\n'
                           '`<first name> <second name>`')
            return
        if group not in (role.name for role in guild.roles):
            await ctx.send('It seems like this group do not exist (yet)! '
                           'If you are sure this is not a typo, write to your local admin')
        else:
            await self.notify_admin_new_guild_member(member.id, member.nick, group)
            await ctx.send(f'Registered your request to join {group} group! '
                           f'You will have to wait for some time before admin approves this. '
                           f'I will notify you about the decision once it\'s made')

    async def notify_admin_new_guild_member(self, member_id: int, nickname: str, group: str):
        admin = await self.get_admin()
        msg = await admin.send(f'New request to join server!\n'
                               f'Nickname: {nickname}\n'
                               f'Group: {group}')
        await asyncio.gather(
            msg.add_reaction(EMOJI_CHECK_MARK),
            msg.add_reaction(EMOJI_CROSS_MARK)
        )
        self.awaiting_approval[msg.id] = (member_id, group)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: User):
        if user.id != self.admin_id:
            return
        try:
            member_id, group = self.awaiting_approval[reaction.message.id]
        except KeyError:
            return

        guild, admin = await asyncio.gather(
            self.get_guild(),
            self.get_admin()
        )
        member: Member = await guild.fetch_member(member_id)
        if reaction.emoji == EMOJI_CHECK_MARK:
            print(f'Adding {member.nick} to {group}')
            for role in guild.roles:
                if role.name == group:
                    await member.add_roles(role, reason='Admin approved through reaction')
                    await member.send('Your request has been approved. Welcome to the server!')
                    return
            else:
                admin = await self.get_admin()
                await admin.send(f'Unable to grant role "{group}" to {member.id} '
                                 f'aka {member.nick} because such group does not exist!')
        else:
            await member.send('Your request has been declined. '
                              'Write admin if you think this is an act of injustice')

    @commands.command()
    async def context(self, ctx: Context):
        user: User = ctx.author
        await user.send(f'User id: {ctx.author.id}\n'
                        f'Guild id: {ctx.guild.id}')


class SUAIBot(Bot):
    async def on_ready(self):
        print('Successfully started bot!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Small bot to manage your uni discord needs")
    parser.add_argument('--config', default='config.toml', help='config file to use')
    args = parser.parse_args()
    print('Reading config file...')
    with open(args.config, 'r') as file:
        config = toml.load(file)

    print('Starting bot...')
    bot = SUAIBot(command_prefix='!')
    bot.add_cog(Greeter(bot, admin_id=config['server']['admin_id'], guild_id=config['server']['id']))
    bot.run(config['token'])
