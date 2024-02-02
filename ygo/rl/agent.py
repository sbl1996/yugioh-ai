import torch
import torch.nn as nn


def bytes_to_bin(x, points, intervals):
    x = x[..., 0] * 256 + x[..., 1]
    x = x.unsqueeze(-1)
    return torch.clamp((x - points + intervals) / intervals, 0, 1)
 

def make_bin_params(x_max=32000, n_bins=32, sig_bins=24):
    x_max1 = 8000
    x_max2 = x_max
    points1 = torch.linspace(0, x_max1, sig_bins + 1, dtype=torch.float32)[1:]
    points2 = torch.linspace(x_max1, x_max2, n_bins - sig_bins + 1, dtype=torch.float32)[1:]
    points = torch.cat([points1, points2], dim=0)
    intervals = torch.cat([points[0:1], points[1:] - points[:-1]], dim=0)
    return points, intervals


class Agent(nn.Module):

    def __init__(self, channels=128, num_card_layers=2, num_action_layers=2, embedding_shape=None, bias=False):
        super(Agent, self).__init__()
        c = channels
        self.location_embed = nn.Embedding(9, c)
        self.seq_embed = nn.Embedding(41, c)

        linear = lambda in_features, out_features: nn.Linear(in_features, out_features, bias=bias)

        if embedding_shape is None:
            n_embed, embed_dim = 110, 1024
        else:
            n_embed, embed_dim = embedding_shape
            n_embed = 1 + n_embed  # 1 (index 0) for unknown
        self.id_text_embed = nn.Embedding(n_embed, embed_dim)
        self.id_text_fc_emb = linear(1024, c // 2)
        self.id_norm = nn.LayerNorm(c // 2, elementwise_affine=False)

        c_num = c // 8
        n_bins = 32
        self.num_fc_emb = nn.Sequential(
            linear(n_bins, c_num),
            nn.ReLU(),
        )
        bin_points, bin_intervals = make_bin_params(n_bins=n_bins)
        self.bin_points = nn.Parameter(bin_points, requires_grad=False)
        self.bin_intervals = nn.Parameter(bin_intervals, requires_grad=False)

        self.owner_embed = nn.Embedding(2, c // 16)
        self.position_embed = nn.Embedding(9, c // 16)
        self.attribute_embed = nn.Embedding(8, c // 16)
        self.race_embed = nn.Embedding(27, c // 16)
        self.level_embed = nn.Embedding(14, c // 16)
        self.type_fc_emb = linear(25, c // 16)
        self.atk_fc_emb = linear(c_num, c // 16)
        self.def_fc_emb = linear(c_num, c // 16)
        self.feat_norm = nn.LayerNorm(c // 2, elementwise_affine=False)

        self.na_card_embed = nn.Parameter(torch.randn(1, c))

        num_heads = max(2, c // 128)
        self.card_net = nn.ModuleList([
            nn.TransformerEncoderLayer(
                c, num_heads, c * 4, dropout=0.0, batch_first=True, norm_first=True)
            for i in range(num_card_layers)
        ])

        self.card_norm = nn.LayerNorm(c, elementwise_affine=False)

        self.lp_fc_emb = linear(c_num, c // 4)
        self.oppo_lp_fc_emb = linear(c_num, c // 4)
        self.phase_embed = nn.Embedding(10, c // 4)
        self.if_first_embed = nn.Embedding(2, c // 8)
        self.is_my_turn_embed = nn.Embedding(2, c // 8)

        self.global_norm_pre = nn.LayerNorm(c, elementwise_affine=False)
        self.global_net = nn.Sequential(
            nn.Linear(c, c),
            nn.ReLU(),
            nn.Linear(c, c),
        )
        self.global_norm = nn.LayerNorm(c, elementwise_affine=False)

        self.fusion = nn.Sequential(
            nn.Linear(c * 2, c),
            nn.ReLU(),
        )

        self.a_msg_embed = nn.Embedding(16, c // 16 * 3)
        self.a_act_embed = nn.Embedding(8, c // 16)
        self.a_yesno_embed = nn.Embedding(3, c // 16)
        self.a_phase_embed = nn.Embedding(4, c // 16)
        self.a_cancel_embed = nn.Embedding(2, c // 16)
        self.a_position_embed = nn.Embedding(5, c // 16)

        self.a_card_proj = nn.Linear(c, c // 2)

        num_heads = max(2, c // 128)
        self.action_net = nn.ModuleList([
            nn.TransformerDecoderLayer(
                c, num_heads, c * 4, dropout=0.0, batch_first=True, norm_first=True)
            for i in range(num_action_layers)
        ])

        self.action_norm = nn.LayerNorm(c, elementwise_affine=False)
        self.value_head = nn.Sequential(
            nn.Linear(c, c // 4),
            nn.ReLU(),
            nn.Linear(c // 4, 1),
        )

    def load_embeddings(self, embeddings):
        weight = self.id_text_embed.weight
        embeddings = torch.from_numpy(embeddings).to(dtype=weight.dtype, device=weight.device)
        unknown_embed = embeddings.mean(dim=0, keepdim=True)
        embeddings = torch.cat([unknown_embed, embeddings], dim=0)
        weight.data.copy_(embeddings)
        weight.requires_grad = False

    def num_transform(self, x):
        return self.num_fc_emb(bytes_to_bin(x, self.bin_points, self.bin_intervals))

    def forward(self, x):
        x_cards = x['cards_']
        x_global = x['global_']
        x_actions = x['actions_']
        
        x_cards_1 = x_cards[:, :, :8].long()
        x_id = x_cards_1[:, :, 0]
        x_id = self.id_text_embed(x_id)
        x_id = self.id_text_fc_emb(x_id)
        x_id = self.id_norm(x_id)
        
        f_location = self.location_embed(x_cards_1[:, :, 1])
        f_seq = self.seq_embed(x_cards_1[:, :, 2])

        x_owner = self.owner_embed(x_cards_1[:, :, 3])
        x_position = self.position_embed(x_cards_1[:, :, 4])
        x_attribute = self.attribute_embed(x_cards_1[:, :, 5])
        x_race = self.race_embed(x_cards_1[:, :, 6])
        x_level = self.level_embed(x_cards_1[:, :, 7])

        x_cards_2 = x_cards[:, :, 8:].to(torch.float32)
        x_atk = self.num_transform(x_cards_2[:, :, 0:2])
        x_atk = self.atk_fc_emb(x_atk)
        x_def = self.num_transform(x_cards_2[:, :, 2:4])
        x_def = self.def_fc_emb(x_def)
        x_type = self.type_fc_emb(x_cards_2[:, :, 4:])

        x_feat = torch.cat([
            x_owner, x_position, x_attribute, x_race, x_level, x_atk, x_def, x_type
        ], dim=-1)
        x_feat = self.feat_norm(x_feat)

        f_cards = torch.cat([x_id, x_feat], dim=-1)
        f_cards = f_cards + f_location + f_seq

        f_na_card = self.na_card_embed.expand(f_cards.shape[0], -1, -1)
        f_cards = torch.cat([f_na_card, f_cards], dim=1)

        for layer in self.card_net:
            f_cards = layer(f_cards)
        f_cards = self.card_norm(f_cards)
        
        x_global_1 = x_global[:, :4].float()
        x_g_lp = self.lp_fc_emb(self.num_transform(x_global_1[:, 0:2]))
        x_g_oppo_lp = self.oppo_lp_fc_emb(self.num_transform(x_global_1[:, 2:4]))

        x_global_2 = x_global[:, 4:7].long()
        x_g_phase = self.phase_embed(x_global_2[:, 0])
        x_g_if_first = self.if_first_embed(x_global_2[:, 1])
        x_g_is_my_turn = self.is_my_turn_embed(x_global_2[:, 2])
        x_global = torch.cat([x_g_lp, x_g_oppo_lp, x_g_phase, x_g_if_first, x_g_is_my_turn], dim=-1)
        x_global = self.global_norm_pre(x_global)
        f_global = self.global_net(x_global)
        f_global = self.global_norm(f_global)
        
        # f_cards_global = torch.cat([f_cards, f_global.unsqueeze(1).expand(-1, f_cards.shape[1], -1)], dim=-1)
        # f_cards = self.fusion(f_cards_global)

        f_cards = f_cards + f_global.unsqueeze(1)

        x_actions = x_actions.long()

        x_card_index = x_actions[:, :, 0]
        B = torch.arange(x_card_index.shape[0], device=x_card_index.device)
        f_a_actions = f_cards[B[:, None], x_card_index]
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
        valid = x['global_'][:, 7] == 0
        mask[:, 0] &= valid
        for layer in self.action_net:
            f_actions = layer(f_actions, f_cards, tgt_key_padding_mask=mask)
        f_actions = self.action_norm(f_actions)
        values = self.value_head(f_actions)[..., 0]
        values = torch.tanh(values)
        values = torch.where(mask, torch.full_like(values, -1.01), values)
        return values, valid