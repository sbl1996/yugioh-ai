import torch
import torch.nn as nn

class Agent(nn.Module):

    def __init__(self, channels=128, num_card_layers=2, num_action_layers=2):
        super(Agent, self).__init__()
        c = channels
        self.location_embed = nn.Embedding(9, c)
        self.seq_embed = nn.Embedding(41, c)

        self.id_text_embed = nn.Embedding(110, 1024)
        self.id_embed = nn.Linear(1024, c // 2)
        self.id_norm = nn.LayerNorm(c // 2, elementwise_affine=False)

        self.owner_embed = nn.Embedding(2, c // 16)
        self.position_embed = nn.Embedding(9, c // 16)
        self.attribute_embed = nn.Embedding(8, c // 16)
        self.race_embed = nn.Embedding(27, c // 16)
        self.level_embed = nn.Embedding(14, c // 16)
        self.type_embed = nn.Linear(25, c // 16)
        self.atk_embed = nn.Linear(16, c // 16)
        self.def_embed = nn.Linear(16, c // 16)
        self.feat_norm = nn.LayerNorm(c // 2, elementwise_affine=False)

        self.na_card_embed = nn.Parameter(torch.randn(1, c))

        self.card_net = nn.ModuleList([
            nn.TransformerEncoderLayer(
                c, c // 128, c * 4, dropout=0.0, batch_first=True, norm_first=True)
            for i in range(num_card_layers)
        ])

        self.card_norm = nn.LayerNorm(c, elementwise_affine=False)

        self.global_net = nn.Sequential(
            nn.Linear(44, c),
            nn.ReLU(),
            nn.Linear(c, c),
        )
        self.global_norm = nn.LayerNorm(c, elementwise_affine=False)

        self.a_msg_embed = nn.Embedding(16, c // 16 * 3)
        self.a_act_embed = nn.Embedding(8, c // 16)
        self.a_yesno_embed = nn.Embedding(3, c // 16)
        self.a_phase_embed = nn.Embedding(4, c // 16)
        self.a_cancel_embed = nn.Embedding(2, c // 16)
        self.a_position_embed = nn.Embedding(5, c // 16)

        self.a_card_proj = nn.Linear(c, c // 2)

        self.action_net = nn.ModuleList([
            nn.TransformerDecoderLayer(
                c, c // 128, c * 4, dropout=0.0, batch_first=True, norm_first=True)
            for i in range(num_action_layers)
        ])

        self.action_norm = nn.LayerNorm(c, elementwise_affine=False)
        self.value_head = nn.Linear(c, 1)

    def forward(self, x):
        x_cards = x['cards']
        x_global = x['global']
        x_actions = x['actions']
        float_dtype = x_global.dtype
        
        x_cards_1 = x_cards[:, :, :8].long()
        x_id = x_cards_1[:, :, 0]
        x_id = self.id_text_embed(x_id)
        x_id = self.id_embed(x_id)
        x_id = self.id_norm(x_id)

        x_owner = self.owner_embed(x_cards_1[:, :, 1])
        x_position = self.position_embed(x_cards_1[:, :, 4])
        x_attribute = self.attribute_embed(x_cards_1[:, :, 5])
        x_race = self.race_embed(x_cards_1[:, :, 6])
        x_level = self.level_embed(x_cards_1[:, :, 7])

        x_cards_2 = x_cards[:, :, 8:].to(float_dtype)
        x_type = self.type_embed(x_cards_2[:, :, :25])
        x_atk = self.atk_embed(x_cards_2[:, :, 25:41])
        x_def = self.def_embed(x_cards_2[:, :, 41:57])
        x_feat = torch.cat([
            x_owner, x_position, x_attribute, x_race, x_level, x_type, x_atk, x_def
        ], dim=-1)
        x_feat = self.feat_norm(x_feat)

        f_cards = torch.cat([x_id, x_feat], dim=-1)
        f_cards += self.location_embed(x_cards_1[:, :, 2])
        f_cards += self.seq_embed(x_cards_1[:, :, 3])

        f_na_card = self.na_card_embed.expand(f_cards.shape[0], -1, -1)
        f_cards = torch.cat([f_na_card, f_cards], dim=1)

        for layer in self.card_net:
            f_cards = layer(f_cards)
        f_cards = self.card_norm(f_cards)
        
        f_global = self.global_net(x_global)
        f_global = self.global_norm(f_global)

        f_cards = f_cards + f_global.unsqueeze(1)

        x_actions = x_actions.long()

        x_card_index = x_actions[:, :, 0]
        f_a_actions = f_cards.gather(1, x_card_index.unsqueeze(-1).expand(-1, -1, f_cards.shape[-1]))
        f_a_actions = self.a_card_proj(f_a_actions)

        x_a_msg = self.a_msg_embed(x_actions[:, :, 1])
        x_a_act = self.a_act_embed(x_actions[:, :, 2])
        x_a_yesno = self.a_yesno_embed(x_actions[:, :, 3])
        x_a_phase = self.a_phase_embed(x_actions[:, :, 4])
        x_a_cancel = self.a_cancel_embed(x_actions[:, :, 5])
        x_a_position = self.a_position_embed(x_actions[:, :, 6])
        f_actions = torch.cat([
            f_a_actions, x_a_msg, x_a_act, x_a_yesno, x_a_phase, x_a_cancel, x_a_position
        ], dim=-1)

        
        mask = x_actions[:, :, 1] == 0
        for layer in self.action_net:
            f_actions = layer(f_actions, f_cards, tgt_key_padding_mask=mask)
        f_actions = self.action_norm(f_actions)
        values = self.value_head(f_actions)[..., 0]
        return values