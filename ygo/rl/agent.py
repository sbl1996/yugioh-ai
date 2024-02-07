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

    def __init__(self, channels=128, num_card_layers=2, num_action_layers=2,
                 num_history_action_layers=2, embedding_shape=None, bias=False, affine=True):
        super(Agent, self).__init__()
        self.num_history_action_layers = num_history_action_layers

        c = channels
        self.loc_embed = nn.Embedding(9, c)
        self.loc_norm = nn.LayerNorm(c, elementwise_affine=affine)
        self.seq_embed = nn.Embedding(41, c)
        self.seq_norm = nn.LayerNorm(c, elementwise_affine=affine)

        linear = lambda in_features, out_features: nn.Linear(in_features, out_features, bias=bias)

        c_num = c // 8
        n_bins = 32
        self.num_fc = nn.Sequential(
            linear(n_bins, c_num),
            nn.ReLU(),
        )
        bin_points, bin_intervals = make_bin_params(n_bins=n_bins)
        self.bin_points = nn.Parameter(bin_points, requires_grad=False)
        self.bin_intervals = nn.Parameter(bin_intervals, requires_grad=False)

        if embedding_shape is None:
            n_embed, embed_dim = 110, 1024
        else:
            n_embed, embed_dim = embedding_shape
            n_embed = 1 + n_embed  # 1 (index 0) for unknown
        self.id_embed = nn.Embedding(n_embed, embed_dim)

        self.id_fc_emb = linear(1024, c // 4)

        self.id_norm = nn.LayerNorm(c // 4, elementwise_affine=False)

        self.owner_embed = nn.Embedding(2, c // 16 * 2)
        self.position_embed = nn.Embedding(9, c // 16 * 2)
        self.overley_embed = nn.Embedding(2, c // 16)
        self.attribute_embed = nn.Embedding(8, c // 16)
        self.race_embed = nn.Embedding(27, c // 16)
        self.level_embed = nn.Embedding(14, c // 16)
        self.type_fc_emb = linear(25, c // 16 * 2)
        self.atk_fc_emb = linear(c_num, c // 16)
        self.def_fc_emb = linear(c_num, c // 16)
        self.feat_norm = nn.LayerNorm(c // 4 * 3, elementwise_affine=affine)

        self.na_card_embed = nn.Parameter(torch.randn(1, c) * 0.02, requires_grad=True)

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

        self.global_norm_pre = nn.LayerNorm(c, elementwise_affine=affine)
        self.global_net = nn.Sequential(
            nn.Linear(c, c),
            nn.ReLU(),
            nn.Linear(c, c),
        )
        self.global_norm = nn.LayerNorm(c, elementwise_affine=False)

        divisor = 8
        self.a_msg_embed = nn.Embedding(16, c // divisor * 2)
        self.a_act_embed = nn.Embedding(8, c // divisor)
        self.a_yesno_embed = nn.Embedding(3, c // divisor)
        self.a_phase_embed = nn.Embedding(4, c // divisor)
        self.a_cancel_embed = nn.Embedding(2, c // divisor)
        self.a_position_embed = nn.Embedding(5, c // divisor)
        self.a_option_embed = nn.Embedding(4, c // divisor)
        self.a_feat_norm = nn.LayerNorm(c, elementwise_affine=affine)

        self.a_card_norm = nn.LayerNorm(c, elementwise_affine=False)
        self.a_card_proj = nn.Sequential(
            nn.Linear(c, c),
            nn.ReLU(),
            nn.Linear(c, c),
        )


        self.h_id_fc_emb = linear(1024, c)
        self.h_id_norm = nn.LayerNorm(c, elementwise_affine=False)
        self.h_a_feat_norm = nn.LayerNorm(c, elementwise_affine=False)

        num_heads = max(2, c // 128)
        self.action_card_net = nn.ModuleList([
            nn.TransformerDecoderLayer(
                c, num_heads, c * 4, dropout=0.0, batch_first=True, norm_first=True, bias=False)
            for i in range(num_action_layers)
        ])

        self.action_history_net = nn.ModuleList([
            nn.TransformerDecoderLayer(
                c, num_heads, c * 4, dropout=0.0, batch_first=True, norm_first=True, bias=False)
            for i in range(num_action_layers)
        ])

        self.action_norm = nn.LayerNorm(c, elementwise_affine=False)
        self.value_head = nn.Sequential(
            nn.Linear(c, c // 4),
            nn.ReLU(),
            nn.Linear(c // 4, 1),
        )

        self.init_embeddings()

    def init_embeddings(self, scale=0.0001):
        for n, m in self.named_modules():
            if isinstance(m, nn.Embedding):
                nn.init.uniform_(m.weight, -scale, scale)
            elif n in ["atk_fc_emb", "def_fc_emb"]:
                nn.init.uniform_(m.weight, -scale * 10, scale * 10)
            elif n in ["lp_fc_emb", "oppo_lp_fc_emb"]:
                nn.init.uniform_(m.weight, -scale, scale)
            elif "fc_emb" in n:
                nn.init.uniform_(m.weight, -scale, scale)
            

    def load_embeddings(self, embeddings, freeze=True):
        weight = self.id_embed.weight
        embeddings = torch.from_numpy(embeddings).to(dtype=weight.dtype, device=weight.device)
        unknown_embed = embeddings.mean(dim=0, keepdim=True)
        embeddings = torch.cat([unknown_embed, embeddings], dim=0)
        weight.data.copy_(embeddings)
        if freeze:
            weight.requires_grad = False

    def num_transform(self, x):
        return self.num_fc(bytes_to_bin(x, self.bin_points, self.bin_intervals))

    def encode_action_(self, x):
        x_a_msg = self.a_msg_embed(x[:, :, 1])
        x_a_act = self.a_act_embed(x[:, :, 2])
        x_a_yesno = self.a_yesno_embed(x[:, :, 3])
        x_a_phase = self.a_phase_embed(x[:, :, 4])
        x_a_cancel = self.a_cancel_embed(x[:, :, 5])
        x_a_position = self.a_position_embed(x[:, :, 6])
        x_a_option = self.a_option_embed(x[:, :, 7])
        return x_a_msg, x_a_act, x_a_yesno, x_a_phase, x_a_cancel, x_a_position, x_a_option

    def get_action_card_(self, x, f_cards):
        x_card_index = x[:, :, 0]
        B = torch.arange(x_card_index.shape[0], device=x_card_index.device)
        f_a_actions = f_cards[B[:, None], x_card_index]
        return f_a_actions

    def encode_card_id(self, x):
        x_id = self.id_embed(x)
        x_id = self.id_fc_emb(x_id)
        x_id = self.id_norm(x_id)
        return x_id

    def encode_card_feat1(self, x1):
        x_owner = self.owner_embed(x1[:, :, 3])
        x_position = self.position_embed(x1[:, :, 4])
        x_overley = self.overley_embed(x1[:, :, 5])
        x_attribute = self.attribute_embed(x1[:, :, 6])
        x_race = self.race_embed(x1[:, :, 7])
        x_level = self.level_embed(x1[:, :, 8])
        return x_owner, x_position, x_overley, x_attribute, x_race, x_level
    
    def encode_card_feat2(self, x2):
        x_atk = self.num_transform(x2[:, :, 0:2])
        x_atk = self.atk_fc_emb(x_atk)
        x_def = self.num_transform(x2[:, :, 2:4])
        x_def = self.def_fc_emb(x_def)
        x_type = self.type_fc_emb(x2[:, :, 4:])
        return x_atk, x_def, x_type

    def encode_global(self, x):
        x_global_1 = x[:, :4].float()
        x_g_lp = self.lp_fc_emb(self.num_transform(x_global_1[:, 0:2]))
        x_g_oppo_lp = self.oppo_lp_fc_emb(self.num_transform(x_global_1[:, 2:4]))

        x_global_2 = x[:, 4:-1].long()
        x_g_phase = self.phase_embed(x_global_2[:, 0])
        x_g_if_first = self.if_first_embed(x_global_2[:, 1])
        x_g_is_my_turn = self.is_my_turn_embed(x_global_2[:, 2])

        x_global = torch.cat([x_g_lp, x_g_oppo_lp, x_g_phase, x_g_if_first, x_g_is_my_turn], dim=-1)
        return x_global

    def forward(self, x):
        x_cards = x['cards_']
        x_global = x['global_']
        x_actions = x['actions_']
        x_h_actions = x['history_actions_']
        
        x_cards_1 = x_cards[:, :, :9].long()
        x_cards_2 = x_cards[:, :, 9:].to(torch.float32)

        x_id = self.encode_card_id(x_cards_1[:, :, 0])
        f_loc = self.loc_norm(self.loc_embed(x_cards_1[:, :, 1]))
        f_seq = self.seq_norm(self.seq_embed(x_cards_1[:, :, 2]))

        x_feat1 = self.encode_card_feat1(x_cards_1)
        x_feat2 = self.encode_card_feat2(x_cards_2)

        x_feat = torch.cat([*x_feat1, *x_feat2], dim=-1)
        x_feat = self.feat_norm(x_feat)

        f_cards = torch.cat([x_id, x_feat], dim=-1)
        f_cards = f_cards + f_loc + f_seq

        f_na_card = self.na_card_embed.expand(f_cards.shape[0], -1, -1)
        f_cards = torch.cat([f_na_card, f_cards], dim=1)

        for layer in self.card_net:
            f_cards = layer(f_cards)
        f_cards = self.card_norm(f_cards)
        
        x_global = self.encode_global(x_global)
        x_global = self.global_norm_pre(x_global)
        f_global = x_global + self.global_net(x_global)
        f_global = self.global_norm(f_global)
        
        f_cards = f_cards + f_global.unsqueeze(1)

        x_actions = x_actions.long()

        f_a_cards = self.get_action_card_(x_actions, f_cards)
        f_a_cards = f_a_cards + self.a_card_proj(self.a_card_norm(f_a_cards))

        x_a_feats = self.encode_action_(x_actions)
        x_a_feats = torch.cat(x_a_feats, dim=-1)
        f_actions = f_a_cards + self.a_feat_norm(x_a_feats)

        mask = x_actions[:, :, 1] == 0
        valid = x['global_'][:, -1] == 0
        mask[:, 0] &= valid
        for layer in self.action_card_net:
            f_actions = layer(f_actions, f_cards, tgt_key_padding_mask=mask)

        if self.num_history_action_layers != 0:
            x_h_actions = x_h_actions.long()

            x_h_id = self.id_embed(x_h_actions[:, :, 0])
            x_h_id = self.h_id_fc_emb(x_h_id)

            x_h_a_feats = self.encode_action_(x_h_actions)
            x_h_a_feats = torch.cat(x_h_a_feats, dim=-1)
            f_h_actions = self.h_id_norm(x_h_id) + self.h_a_feat_norm(x_h_a_feats)
            
            for layer in self.action_history_net:
                f_actions = layer(f_actions, f_h_actions)

        f_actions = self.action_norm(f_actions)
        values = self.value_head(f_actions)[..., 0]
        values = torch.tanh(values)
        values = torch.where(mask, torch.full_like(values, -1.01), values)
        return values, valid