import dns from 'dns';
import { Api, Bot } from 'grammy';

// Force IPv4 for Telegram API. IPv6 long-poll connections silently stall
// on some Linux network configurations (connection goes ESTAB with unsent
// bytes in the send buffer, never recovers).
dns.setDefaultResultOrder('ipv4first');

import fs from 'fs';
import path from 'path';

import { ASSISTANT_NAME, TRIGGER_PATTERN } from '../config.js';
import {
  getOnboardingState,
  setOnboardingState,
  type OnboardingState,
} from '../db.js';
import { readEnvFile } from '../env.js';
import { logger } from '../logger.js';
import { registerChannel, ChannelOpts } from './registry.js';
import {
  Channel,
  OnChatMetadata,
  OnInboundMessage,
  RegisteredGroup,
} from '../types.js';

export interface TelegramChannelOpts {
  onMessage: OnInboundMessage;
  onChatMetadata: OnChatMetadata;
  registeredGroups: () => Record<string, RegisteredGroup>;
  getInitialJids: (channelName: string) => string[];
}

/**
 * Send a message with Telegram Markdown parse mode, falling back to plain text.
 * Claude's output naturally matches Telegram's Markdown v1 format:
 *   *bold*, _italic_, `code`, ```code blocks```, [links](url)
 */
async function sendTelegramMessage(
  api: { sendMessage: Api['sendMessage'] },
  chatId: string | number,
  text: string,
  options: { message_thread_id?: number } = {},
): Promise<void> {
  try {
    await api.sendMessage(chatId, text, {
      ...options,
      parse_mode: 'Markdown',
    });
  } catch (err) {
    // Fallback: send as plain text if Markdown parsing fails
    logger.debug({ err }, 'Markdown send failed, falling back to plain text');
    await api.sendMessage(chatId, text, options);
  }
}

/**
 * Load welcome message templates from templates/microhal/welcome/.
 * Files are sorted by name (01-greeting.md, 02-disclaimer.md, etc.)
 * and returned as an array of strings.
 */
function loadWelcomeMessages(): string[] {
  const welcomeDir = path.join(
    process.cwd(),
    'templates',
    'microhal',
    'welcome',
  );
  try {
    const files = fs
      .readdirSync(welcomeDir)
      .filter((f) => f.endsWith('.md'))
      .sort();
    return files.map((f) =>
      fs.readFileSync(path.join(welcomeDir, f), 'utf-8').trim(),
    );
  } catch {
    logger.warn({ welcomeDir }, 'Welcome templates not found');
    return [];
  }
}

/**
 * Write onboarding state to memory/onboarding-state.yaml for agent handoff.
 * The agent reads this file to know where the bot-level onboarding left off.
 */
function writeOnboardingYaml(
  groupFolder: string,
  senderId: string,
  state: OnboardingState,
  waiverAcceptedAt?: string,
): void {
  const groupDir = path.join(process.cwd(), 'groups', groupFolder);
  const memDir = path.join(process.cwd(), 'memory');
  const yamlPath = path.join(memDir, 'onboarding-state.yaml');

  const content =
    [
      `state: ${state}`,
      `sender_id: "${senderId}"`,
      `group_folder: "${groupFolder}"`,
      waiverAcceptedAt ? `waiver_accepted_at: "${waiverAcceptedAt}"` : null,
      `transitions:`,
      `  - to: ${state}`,
      `    at: "${new Date().toISOString()}"`,
    ]
      .filter(Boolean)
      .join('\n') + '\n';

  try {
    fs.mkdirSync(memDir, { recursive: true });
    fs.writeFileSync(yamlPath, content);
  } catch (err) {
    logger.warn({ err, yamlPath }, 'Failed to write onboarding YAML');
  }
}

/**
 * Send the welcome sequence to a new user.
 * Messages 01-03 are sent immediately; 04 (ready) is sent after waiver acceptance.
 */
async function sendWelcomeSequence(
  api: { sendMessage: Api['sendMessage'] },
  chatId: string | number,
  upToIndex: number,
): Promise<void> {
  const messages = loadWelcomeMessages();
  const toSend = messages.slice(0, upToIndex);
  for (const text of toSend) {
    await sendTelegramMessage(api, chatId, text);
    // Brief pause between messages for natural pacing
    await new Promise((r) => setTimeout(r, 1000));
  }
}

// Bot pool for agent teams: send-only Api instances (no polling)
const poolApis: Api[] = [];
// Maps "{groupFolder}:{senderName}" → pool Api index for stable assignment
const senderBotMap = new Map<string, number>();
let nextPoolIndex = 0;

/**
 * Initialize send-only Api instances for the bot pool.
 * Each pool bot can send messages but doesn't poll for updates.
 */
export async function initBotPool(tokens: string[]): Promise<void> {
  for (const token of tokens) {
    try {
      const api = new Api(token);
      const me = await api.getMe();
      poolApis.push(api);
      logger.info(
        { username: me.username, id: me.id, poolSize: poolApis.length },
        'Pool bot initialized',
      );
    } catch (err) {
      logger.error({ err }, 'Failed to initialize pool bot');
    }
  }
  if (poolApis.length > 0) {
    logger.info({ count: poolApis.length }, 'Telegram bot pool ready');
  }
}

/**
 * Send a message via a pool bot assigned to the given sender name.
 * Assigns bots round-robin on first use; subsequent messages from the
 * same sender in the same group always use the same bot.
 * On first assignment, renames the bot to match the sender's role.
 */
export async function sendPoolMessage(
  chatId: string,
  text: string,
  sender: string,
  groupFolder: string,
): Promise<void> {
  if (poolApis.length === 0) return;

  const key = `${groupFolder}:${sender}`;
  let idx = senderBotMap.get(key);
  if (idx === undefined) {
    idx = nextPoolIndex % poolApis.length;
    nextPoolIndex++;
    senderBotMap.set(key, idx);
    // Rename the bot to match the sender's role, then wait for Telegram to propagate
    try {
      await poolApis[idx].setMyName(sender);
      await new Promise((r) => setTimeout(r, 2000));
      logger.info(
        { sender, groupFolder, poolIndex: idx },
        'Assigned and renamed pool bot',
      );
    } catch (err) {
      logger.warn(
        { sender, err },
        'Failed to rename pool bot (sending anyway)',
      );
    }
  }

  const api = poolApis[idx];
  try {
    const numericId = chatId.replace(/^tg:/, '');
    const MAX_LENGTH = 4096;
    if (text.length <= MAX_LENGTH) {
      await sendTelegramMessage(api, numericId, text);
    } else {
      for (let i = 0; i < text.length; i += MAX_LENGTH) {
        await sendTelegramMessage(
          api,
          numericId,
          text.slice(i, i + MAX_LENGTH),
        );
      }
    }
    logger.info(
      { chatId, sender, poolIndex: idx, length: text.length },
      'Pool message sent',
    );
  } catch (err) {
    logger.error({ chatId, sender, err }, 'Failed to send pool message');
  }
}

export class TelegramChannel implements Channel {
  name: string;

  private bot: Bot | null = null;
  private opts: TelegramChannelOpts;
  private botToken: string;
  /** JIDs this bot instance has received messages from (used for routing). */
  private ownedJids = new Set<string>();

  constructor(
    botToken: string,
    opts: TelegramChannelOpts,
    channelName = 'telegram',
  ) {
    this.name = channelName;
    this.botToken = botToken;
    this.opts = opts;
  }

  async connect(): Promise<void> {
    // Restore JID ownership from DB so routing works on restart without waiting
    // for the first inbound message.
    for (const jid of this.opts.getInitialJids(this.name)) {
      this.ownedJids.add(jid);
    }

    this.bot = new Bot(this.botToken);

    // Command to get chat ID (useful for registration)
    this.bot.command('chatid', (ctx) => {
      const chatId = ctx.chat.id;
      const chatType = ctx.chat.type;
      const chatName =
        chatType === 'private'
          ? ctx.from?.first_name || 'Private'
          : (ctx.chat as any).title || 'Unknown';

      ctx.reply(
        `Chat ID: \`tg:${chatId}\`\nName: ${chatName}\nType: ${chatType}`,
        { parse_mode: 'Markdown' },
      );
    });

    // Command to check bot status
    this.bot.command('ping', (ctx) => {
      ctx.reply(`${ASSISTANT_NAME} is online.`);
    });

    // Welcome/onboarding: /start (Telegram default) and /welcome (re-runnable)
    const handleWelcome = async (ctx: any) => {
      const senderId = ctx.from?.id?.toString() || '';
      const chatJid = `tg:${ctx.chat.id}`;
      if (!senderId) return;

      // Send messages 01-03 (greeting, disclaimer, waiver)
      await sendWelcomeSequence(ctx.api, ctx.chat.id, 3);
      setOnboardingState(senderId, chatJid, 'welcome_sent');

      const group = this.opts.registeredGroups()[chatJid];
      if (group) {
        writeOnboardingYaml(group.folder, senderId, 'welcome_sent');
      }

      logger.info(
        { chatJid, senderId },
        'Welcome sequence sent, awaiting waiver acceptance',
      );
    };
    this.bot.command('start', handleWelcome);
    this.bot.command('welcome', handleWelcome);

    // Telegram bot commands handled above — skip them in the general handler
    // so they don't also get stored as messages. All other /commands flow through.
    const TELEGRAM_BOT_COMMANDS = new Set([
      'chatid',
      'ping',
      'start',
      'welcome',
    ]);

    this.bot.on('message:text', async (ctx) => {
      if (ctx.message.text.startsWith('/')) {
        const cmd = ctx.message.text.slice(1).split(/[\s@]/)[0].toLowerCase();
        if (TELEGRAM_BOT_COMMANDS.has(cmd)) return;
      }

      const chatJid = `tg:${ctx.chat.id}`;
      // Claim this JID for this bot instance so routing works
      this.ownedJids.add(chatJid);

      let content = ctx.message.text;
      const timestamp = new Date(ctx.message.date * 1000).toISOString();
      const senderName =
        ctx.from?.first_name ||
        ctx.from?.username ||
        ctx.from?.id.toString() ||
        'Unknown';
      const sender = ctx.from?.id.toString() || '';

      // Onboarding gate: if sender is awaiting waiver acceptance, intercept YES/NO
      if (sender) {
        const onboarding = getOnboardingState(sender);
        if (onboarding?.state === 'welcome_sent') {
          const reply = content.trim().toUpperCase();
          if (reply === 'YES') {
            const now = new Date().toISOString();
            setOnboardingState(sender, chatJid, 'waiver_accepted', now);
            // Send only the "ready" message (04, index 3)
            const messages = loadWelcomeMessages();
            if (messages[3]) {
              await sendTelegramMessage(ctx.api, ctx.chat.id, messages[3]);
            }
            // Advance to active — agent takes over from here
            setOnboardingState(sender, chatJid, 'active');
            const group = this.opts.registeredGroups()[chatJid];
            if (group) {
              writeOnboardingYaml(group.folder, sender, 'active', now);
            }
            logger.info(
              { chatJid, sender },
              'Waiver accepted, onboarding complete',
            );
            return;
          } else {
            // Not YES — gently redirect
            await sendTelegramMessage(
              ctx.api,
              ctx.chat.id,
              "No rush. Reply YES when you're ready to accept, or ask Rick if you have questions.",
            );
            return;
          }
        }
      }
      const msgId = ctx.message.message_id.toString();

      // Determine chat name
      const chatName =
        ctx.chat.type === 'private'
          ? senderName
          : (ctx.chat as any).title || chatJid;

      // Translate Telegram @bot_username mentions into TRIGGER_PATTERN format.
      // Telegram @mentions (e.g., @andy_ai_bot) won't match TRIGGER_PATTERN
      // (e.g., ^@HAL\b), so we prepend the trigger when the bot is @mentioned.
      const botUsername = ctx.me?.username?.toLowerCase();
      if (botUsername) {
        const entities = ctx.message.entities || [];
        const isBotMentioned = entities.some((entity) => {
          if (entity.type === 'mention') {
            const mentionText = content
              .substring(entity.offset, entity.offset + entity.length)
              .toLowerCase();
            return mentionText === `@${botUsername}`;
          }
          return false;
        });
        if (isBotMentioned && !TRIGGER_PATTERN.test(content)) {
          content = `@${ASSISTANT_NAME} ${content}`;
        }
      }

      // Store chat metadata for discovery
      const isGroup =
        ctx.chat.type === 'group' || ctx.chat.type === 'supergroup';
      this.opts.onChatMetadata(
        chatJid,
        timestamp,
        chatName,
        this.name,
        isGroup,
      );

      // Only deliver full message for registered groups
      const group = this.opts.registeredGroups()[chatJid];
      if (!group) {
        logger.debug(
          { chatJid, chatName },
          'Message from unregistered Telegram chat',
        );
        return;
      }

      // Deliver message — startMessageLoop() will pick it up
      this.opts.onMessage(chatJid, {
        id: msgId,
        chat_jid: chatJid,
        sender,
        sender_name: senderName,
        content,
        timestamp,
        is_from_me: false,
      });

      logger.info(
        { chatJid, chatName, sender: senderName },
        'Telegram message stored',
      );
    });

    // Handle non-text messages with placeholders so the agent knows something was sent
    const storeNonText = (ctx: any, placeholder: string) => {
      const chatJid = `tg:${ctx.chat.id}`;
      this.ownedJids.add(chatJid);
      const group = this.opts.registeredGroups()[chatJid];
      if (!group) return;

      const timestamp = new Date(ctx.message.date * 1000).toISOString();
      const senderName =
        ctx.from?.first_name ||
        ctx.from?.username ||
        ctx.from?.id?.toString() ||
        'Unknown';
      const caption = ctx.message.caption ? ` ${ctx.message.caption}` : '';

      const isGroup =
        ctx.chat.type === 'group' || ctx.chat.type === 'supergroup';
      this.opts.onChatMetadata(
        chatJid,
        timestamp,
        undefined,
        this.name,
        isGroup,
      );
      this.opts.onMessage(chatJid, {
        id: ctx.message.message_id.toString(),
        chat_jid: chatJid,
        sender: ctx.from?.id?.toString() || '',
        sender_name: senderName,
        content: `${placeholder}${caption}`,
        timestamp,
        is_from_me: false,
      });
    };

    this.bot.on('message:photo', (ctx) => storeNonText(ctx, '[Photo]'));
    this.bot.on('message:video', (ctx) => storeNonText(ctx, '[Video]'));
    this.bot.on('message:voice', (ctx) => storeNonText(ctx, '[Voice message]'));
    this.bot.on('message:audio', (ctx) => storeNonText(ctx, '[Audio]'));
    this.bot.on('message:document', (ctx) => {
      const name = ctx.message.document?.file_name || 'file';
      storeNonText(ctx, `[Document: ${name}]`);
    });
    this.bot.on('message:sticker', (ctx) => {
      const emoji = ctx.message.sticker?.emoji || '';
      storeNonText(ctx, `[Sticker ${emoji}]`);
    });
    this.bot.on('message:location', (ctx) => storeNonText(ctx, '[Location]'));
    this.bot.on('message:contact', (ctx) => storeNonText(ctx, '[Contact]'));

    // Handle errors gracefully — log full error, not just message
    this.bot.catch((err) => {
      logger.error(
        { err: err.error || err.message, ctx: err.ctx?.update?.update_id },
        'Telegram bot error',
      );
    });

    // Start polling — returns a Promise that resolves when started
    return new Promise<void>((resolve) => {
      this.bot!.start({
        allowed_updates: ['message', 'callback_query'],
        onStart: (botInfo) => {
          logger.info(
            { username: botInfo.username, id: botInfo.id },
            'Telegram bot connected',
          );
          console.log(`\n  Telegram bot: @${botInfo.username}`);
          console.log(
            `  Send /chatid to the bot to get a chat's registration ID\n`,
          );
          resolve();
        },
      });
    });
  }

  async sendMessage(jid: string, text: string): Promise<void> {
    if (!this.bot) {
      logger.warn('Telegram bot not initialized');
      return;
    }

    try {
      const numericId = jid.replace(/^tg:/, '');

      // Telegram has a 4096 character limit per message — split if needed
      const MAX_LENGTH = 4096;
      if (text.length <= MAX_LENGTH) {
        await sendTelegramMessage(this.bot.api, numericId, text);
      } else {
        for (let i = 0; i < text.length; i += MAX_LENGTH) {
          await sendTelegramMessage(
            this.bot.api,
            numericId,
            text.slice(i, i + MAX_LENGTH),
          );
        }
      }
      logger.info({ jid, length: text.length }, 'Telegram message sent');
    } catch (err) {
      logger.error({ jid, err }, 'Failed to send Telegram message');
    }
  }

  isConnected(): boolean {
    return this.bot !== null;
  }

  ownsJid(jid: string): boolean {
    if (!jid.startsWith('tg:')) return false;
    // If we have prior knowledge, only own what we've seen
    if (this.ownedJids.size > 0) return this.ownedJids.has(jid);
    // Bootstrap: no history yet — claim all tg: JIDs (first bot wins in findChannel)
    return true;
  }

  async disconnect(): Promise<void> {
    if (this.bot) {
      this.bot.stop();
      this.bot = null;
      logger.info('Telegram bot stopped');
    }
  }

  async setTyping(jid: string, isTyping: boolean): Promise<void> {
    if (!this.bot || !isTyping) return;
    try {
      const numericId = jid.replace(/^tg:/, '');
      await this.bot.api.sendChatAction(numericId, 'typing');
    } catch (err) {
      logger.debug({ jid, err }, 'Failed to send Telegram typing indicator');
    }
  }
}

registerChannel('telegram', (opts: ChannelOpts) => {
  const envVars = readEnvFile(['TELEGRAM_BOT_TOKEN']);
  const token =
    process.env.TELEGRAM_BOT_TOKEN || envVars.TELEGRAM_BOT_TOKEN || '';
  if (!token) {
    logger.warn('Telegram: TELEGRAM_BOT_TOKEN not set');
    return null;
  }
  return new TelegramChannel(token, opts, 'telegram');
});
