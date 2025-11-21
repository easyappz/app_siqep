import React, { useCallback, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { AuthContext, useAuth } from '../../context/AuthContext';
import { getProfile, fetchProfileStats, updateProfile } from '../../api/profile';
import {
  fetchReferralTree,
  fetchReferralRewards,
  getReferralBonuses,
  getReferralDeposits,
  getReferralRanks,
} from '../../api/referrals';
import { createWithdrawalRequest, getMyWithdrawalRequests } from '../../api/withdrawals';
import { changePassword } from '../../api/auth';
import {
  getWalletSummary,
  getWalletTransactions,
  createWalletDeposit,
} from '../../api/wallet';

function getUserTypeFromMember(member) {
  if (!member) {
    return 'player';
  }

  if (member.user_type) {
    return member.user_type;
  }

  if (member.is_influencer) {
    return 'influencer';
  }

  return 'player';
}

function getUserTypeLabel(userType) {
  if (userType === 'influencer') {
    return 'Инфлюенсер';
  }
  return 'Игрок';
}

function getRankLabel(rank) {
  if (rank === 'silver') {
    return 'Серебряный';
  }
  if (rank === 'gold') {
    return 'Золотой';
  }
  if (rank === 'platinum') {
    return 'Платиновый';
  }
  return 'Стандарт';
}

function getSafeMultiplier(value, fallback = 1) {
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num) || num <= 0) {
    return fallback;
  }
  return num;
}

function getPlayerRewardDescription(rankLabel, rankCode, rankRules, currentRankRuleFallback) {
  const baseDepthBonus = 100;

  const ruleFromList = Array.isArray(rankRules)
    ? rankRules.find((rule) => rule && rule.rank === rankCode)
    : null;

  const effectiveRule = ruleFromList || currentRankRuleFallback || null;

  const multiplier = effectiveRule
    ? getSafeMultiplier(effectiveRule.player_depth_bonus_multiplier, 1)
    : 1;

  const depthBonus = baseDepthBonus * multiplier;
  const depthBonusText = `${depthBonus} V-Coins`;

  return [
    `Ваш текущий ранг: ${rankLabel}.`,
    'За каждого прямого реферала (уровень 1), который впервые приходит в клуб и играет первый платный турнир, вы получаете 1000 V-Coins (эквивалент стартового стека).',
    `За рефералов на уровнях 2–10 вы получаете глубинный кэшбэк: ${depthBonusText} за первый турнир каждого игрока в цепочке. Базовый размер глубинного бонуса — 100 V-Coins, а итоговая величина зависит от множителя ранга.`,
  ];
}

function getInfluencerRewardDescription(rankLabel, rankCode, rankRules, currentRankRuleFallback) {
  const baseDirectBonus = 500;
  const baseDepthBonus = 50;

  const ruleFromList = Array.isArray(rankRules)
    ? rankRules.find((rule) => rule && rule.rank === rankCode)
    : null;

  const effectiveRule = ruleFromList || currentRankRuleFallback || null;

  const multiplier = effectiveRule
    ? getSafeMultiplier(effectiveRule.influencer_depth_bonus_multiplier, 1)
    : 1;

  const depthBonus = baseDepthBonus * multiplier;
  const depthBonusText = `${depthBonus} ₽`;

  return [
    `Ваш текущий ранг: ${rankLabel}.`,
    `За прямого реферала (уровень 1) вы получаете ${baseDirectBonus} ₽ за его первый турнир.`,
    `За рефералов на уровнях 2–10 вы получаете глубинный кэшбэк: ${depthBonusText} за первый турнир каждого нового игрока в цепочке. Базовый размер глубинного бонуса — 50 ₽, а итоговая величина зависит от множителя ранга.`,
    'Дополнительно вы всегда получаете 10% со всех дальнейших депозитов каждого вашего прямого реферала на фишки, независимо от ранга.',
  ];
}

const ProfilePage = () => {
  const { member } = useContext(AuthContext);
  const { logout, setMember } = useAuth();
  const navigate = useNavigate();

  const [profileData, setProfileData] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copyStatus, setCopyStatus] = useState('');

  const [treeData, setTreeData] = useState([]);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [treeError, setTreeError] = useState('');

  const [rewardsData, setRewardsData] = useState(null);
  const [isLoadingRewards, setIsLoadingRewards] = useState(false);
  const [rewardsError, setRewardsError] = useState('');

  const [bankDetails, setBankDetails] = useState('');
  const [cryptoWallet, setCryptoWallet] = useState('');
  const [isSavingPayout, setIsSavingPayout] = useState(false);
  const [payoutError, setPayoutError] = useState('');
  const [payoutSuccess, setPayoutSuccess] = useState('');

  const [withdrawalMethod, setWithdrawalMethod] = useState('card');
  const [withdrawalDestination, setWithdrawalDestination] = useState('');
  const [withdrawalAmount, setWithdrawalAmount] = useState('');
  const [isSubmittingWithdrawal, setIsSubmittingWithdrawal] = useState(false);
  const [withdrawalError, setWithdrawalError] = useState('');
  const [withdrawalSuccess, setWithdrawalSuccess] = useState('');
  const [withdrawals, setWithdrawals] = useState([]);
  const [isLoadingWithdrawals, setIsLoadingWithdrawals] = useState(false);
  const [withdrawalsError, setWithdrawalsError] = useState('');

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [changePasswordErrors, setChangePasswordErrors] = useState({});
  const [changePasswordSuccess, setChangePasswordSuccess] = useState('');

  const [walletSummary, setWalletSummary] = useState(null);
  const [walletLoading, setWalletLoading] = useState(false);
  const [walletError, setWalletError] = useState('');

  const [walletTransactions, setWalletTransactions] = useState([]);
  const [walletTransactionsLoading, setWalletTransactionsLoading] = useState(false);
  const [walletTransactionsError, setWalletTransactionsError] = useState('');
  const [walletTransactionsPage, setWalletTransactionsPage] = useState(1);
  const [walletTransactionsHasNext, setWalletTransactionsHasNext] = useState(false);
  const [walletTransactionsHasPrev, setWalletTransactionsHasPrev] = useState(false);
  const [walletTransactionsTotalCount, setWalletTransactionsTotalCount] = useState(null);

  const [walletDepositAmount, setWalletDepositAmount] = useState('');
  const [walletDepositComment, setWalletDepositComment] = useState('');
  const [walletDepositError, setWalletDepositError] = useState('');
  const [walletDepositSuccess, setWalletDepositSuccess] = useState('');
  const [isSubmittingDeposit, setIsSubmittingDeposit] = useState(false);

  const [referralBonuses, setReferralBonuses] = useState([]);
  const [referralBonusesLoading, setReferralBonusesLoading] = useState(false);
  const [referralBonusesError, setReferralBonusesError] = useState('');

  const [referralDeposits, setReferralDeposits] = useState([]);
  const [referralDepositsLoading, setReferralDepositsLoading] = useState(false);
  const [referralDepositsError, setReferralDepositsError] = useState('');

  const [rankRules, setRankRules] = useState([]);
  const [rankRulesLoading, setRankRulesLoading] = useState(false);
  const [rankRulesError, setRankRulesError] = useState('');

  const handleCopyLink = async (link) => {
    if (!link) {
      return;
    }

    try {
      if (
        typeof navigator !== 'undefined' &&
        navigator.clipboard &&
        navigator.clipboard.writeText
      ) {
        await navigator.clipboard.writeText(link);
        setCopyStatus('Скопировано');
      } else {
        setCopyStatus('Скопируйте ссылку вручную');
      }
    } catch (copyError) {
      setCopyStatus('Не удалось скопировать');
    }

    window.setTimeout(() => {
      setCopyStatus('');
    }, 2000);
  };

  const loadProfile = useCallback(async () => {
    setProfileLoading(true);

    try {
      const data = await getProfile();
      setProfileData(data || null);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
      }
    } finally {
      setProfileLoading(false);
    }
  }, [logout, navigate]);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const data = await fetchProfileStats();
      setStats(data || null);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setError('Не удалось загрузить статистику. Попробуйте еще раз.');
    } finally {
      setLoading(false);
    }
  }, [logout, navigate]);

  const loadReferralTree = useCallback(async () => {
    setIsLoadingTree(true);
    setTreeError('');

    try {
      const data = await fetchReferralTree();
      const nodes = Array.isArray(data?.nodes)
        ? data.nodes
        : Array.isArray(data)
        ? data
        : [];
      setTreeData(nodes);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setTreeError('Не удалось загрузить структуру рефералов. Попробуйте позже.');
    } finally {
      setIsLoadingTree(false);
    }
  }, [logout, navigate]);

  const loadReferralRewards = useCallback(async () => {
    setIsLoadingRewards(true);
    setRewardsError('');

    try {
      const data = await fetchReferralRewards();
      setRewardsData(data || null);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setRewardsError('Не удалось загрузить вознаграждения. Попробуйте позже.');
    } finally {
      setIsLoadingRewards(false);
    }
  }, [logout, navigate]);

  const loadReferralBonuses = useCallback(async () => {
    setReferralBonusesLoading(true);
    setReferralBonusesError('');

    try {
      const data = await getReferralBonuses();
      const list = Array.isArray(data) ? data : [];
      setReferralBonuses(list);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;
      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      setReferralBonusesError('Не удалось загрузить реферальные бонусы. Попробуйте позже.');
    } finally {
      setReferralBonusesLoading(false);
    }
  }, [logout, navigate]);

  const loadReferralDeposits = useCallback(async () => {
    setReferralDepositsLoading(true);
    setReferralDepositsError('');

    try {
      const data = await getReferralDeposits();
      const list = Array.isArray(data) ? data : [];
      setReferralDeposits(list);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;
      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }
      setReferralDepositsError('Не удалось загрузить депозиты рефералов. Попробуйте позже.');
    } finally {
      setReferralDepositsLoading(false);
    }
  }, [logout, navigate]);

  const loadWithdrawals = useCallback(async () => {
    setIsLoadingWithdrawals(true);
    setWithdrawalsError('');

    try {
      const data = await getMyWithdrawalRequests();
      const list = Array.isArray(data) ? data : [];
      setWithdrawals(list);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setWithdrawalsError('Не удалось загрузить заявки на вывод. Попробуйте позже.');
    } finally {
      setIsLoadingWithdrawals(false);
    }
  }, [logout, navigate]);

  const loadWalletSummary = useCallback(async () => {
    setWalletLoading(true);
    setWalletError('');

    try {
      const data = await getWalletSummary();
      setWalletSummary(data || null);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      let message = 'Не удалось загрузить данные кошелька. Попробуйте ещё раз.';

      if (err && err.response && err.response.data) {
        const responseData = err.response.data;
        if (typeof responseData.detail === 'string') {
          message = responseData.detail;
        } else if (typeof responseData.error === 'string') {
          message = responseData.error;
        } else if (typeof responseData.message === 'string') {
          message = responseData.message;
        }
      }

      setWalletError(message);
    } finally {
      setWalletLoading(false);
    }
  }, [logout, navigate]);

  const loadWalletTransactions = useCallback(
    async (page = 1) => {
      setWalletTransactionsLoading(true);
      setWalletTransactionsError('');

      try {
        const data = await getWalletTransactions({ page });

        let items = [];
        let count = null;
        let next = null;
        let previous = null;

        if (Array.isArray(data)) {
          items = data;
          count = data.length;
        } else if (data && Array.isArray(data.results)) {
          items = data.results;
          count = typeof data.count === 'number' ? data.count : null;
          next = data.next;
          previous = data.previous;
        } else if (data && Array.isArray(data.items)) {
          items = data.items;
          count = typeof data.count === 'number' ? data.count : data.items.length;
          next = data.next;
          previous = data.previous;
        }

        setWalletTransactions(items);
        setWalletTransactionsPage(page);
        setWalletTransactionsTotalCount(
          typeof count === 'number' ? count : items.length,
        );
        setWalletTransactionsHasNext(Boolean(next));
        setWalletTransactionsHasPrev(Boolean(previous));
      } catch (err) {
        const statusCode = err && err.response ? err.response.status : null;

        if (statusCode === 401) {
          logout();
          navigate('/login', { replace: true });
          return;
        }

        let message =
          'Не удалось загрузить историю операций кошелька. Попробуйте ещё раз.';

        if (err && err.response && err.response.data) {
          const responseData = err.response.data;
          if (typeof responseData.detail === 'string') {
            message = responseData.detail;
          } else if (typeof responseData.error === 'string') {
            message = responseData.error;
          } else if (typeof responseData.message === 'string') {
            message = responseData.message;
          }
        }

        setWalletTransactionsError(message);
      } finally {
        setWalletTransactionsLoading(false);
      }
    },
    [logout, navigate],
  );

  const loadRankRules = useCallback(async () => {
    setRankRulesLoading(true);
    setRankRulesError('');

    try {
      const data = await getReferralRanks();
      const list = Array.isArray(data) ? data : [];
      setRankRules(list);
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setRankRulesError(
        'Не удалось загрузить параметры рангов. Интерфейс будет работать в упрощённом режиме.',
      );
    } finally {
      setRankRulesLoading(false);
    }
  }, [logout, navigate]);

  useEffect(() => {
    loadProfile();
    loadStats();
  }, [loadProfile, loadStats]);

  useEffect(() => {
    loadReferralTree();
    loadReferralRewards();
  }, [loadReferralTree, loadReferralRewards]);

  useEffect(() => {
    loadWalletSummary();
    loadWalletTransactions(1);
  }, [loadWalletSummary, loadWalletTransactions]);

  useEffect(() => {
    loadReferralBonuses();
    loadReferralDeposits();

    const intervalId = window.setInterval(() => {
      loadReferralBonuses();
      loadReferralDeposits();
    }, 20000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadReferralBonuses, loadReferralDeposits]);

  useEffect(() => {
    loadRankRules();
  }, [loadRankRules]);

  useEffect(() => {
    if (profileData) {
      setBankDetails(profileData.withdrawal_bank_details || '');
      setCryptoWallet(profileData.withdrawal_crypto_wallet || '');
    }
  }, [profileData]);

  const profileUser = profileData || member || null;

  useEffect(() => {
    if (!profileUser) {
      return;
    }

    const userType = getUserTypeFromMember(profileUser);
    const influencerFlag =
      userType === 'influencer' || Boolean(profileUser.is_influencer);

    if (influencerFlag) {
      loadWithdrawals();
    }
  }, [profileUser, loadWithdrawals]);

  const backendUserType = getUserTypeFromMember(profileUser);
  const accountTypeLabel = getUserTypeLabel(backendUserType);
  const rankCode = profileUser && profileUser.rank ? profileUser.rank : 'standard';
  const rankLabel = getRankLabel(rankCode);

  const vCoinsBalance =
    profileUser && typeof profileUser.v_coins_balance !== 'undefined'
      ? profileUser.v_coins_balance
      : 0;

  const cashBalance =
    profileUser && typeof profileUser.cash_balance !== 'undefined'
      ? profileUser.cash_balance
      : 0;

  const directReferralsCount =
    profileUser && typeof profileUser.direct_referrals_count === 'number'
      ? profileUser.direct_referrals_count
      : 0;

  const activeDirectReferralsCount =
    profileUser && typeof profileUser.active_direct_referrals_count === 'number'
      ? profileUser.active_direct_referrals_count
      : 0;

  const currentRankRule = profileUser && profileUser.current_rank_rule
    ? profileUser.current_rank_rule
    : null;

  const referralCode = profileUser && profileUser.referral_code ? profileUser.referral_code : '';

  const referralLink =
    typeof window !== 'undefined'
      ? `${window.location.origin}/register${referralCode ? `?ref=${referralCode}` : ''}`
      : '';

  const totalReferrals =
    stats && typeof stats.total_referrals !== 'undefined' ? stats.total_referrals : 0;

  const activeReferrals =
    stats && typeof stats.active_referrals !== 'undefined' ? stats.active_referrals : 0;

  const totalBonusPoints =
    stats && typeof stats.total_bonus_points !== 'undefined'
      ? stats.total_bonus_points
      : 0;

  const totalMoneyEarned =
    stats && typeof stats.total_money_earned !== 'undefined'
      ? stats.total_money_earned
      : 0;

  const chartData =
    stats && Array.isArray(stats.registrations_chart) ? stats.registrations_chart : [];

  const history = stats && Array.isArray(stats.history) ? stats.history : [];

  const myDepositsTotalAmount =
    stats && typeof stats.my_deposits_total_amount === 'number'
      ? stats.my_deposits_total_amount
      : 0;

  const myDepositsCount =
    stats && typeof stats.my_deposits_count === 'number'
      ? stats.my_deposits_count
      : 0;

  const myDeposits =
    stats && Array.isArray(stats.my_deposits)
      ? stats.my_deposits
      : [];

  const referralTotalDepositsAmount =
    stats && typeof stats.referral_total_deposits_amount === 'number'
      ? stats.referral_total_deposits_amount
      : 0;

  const referralTotalBonusesAmount =
    stats && typeof stats.referral_total_bonuses_amount === 'number'
      ? stats.referral_total_bonuses_amount
      : 0;

  const levelSummaryFromStats =
    stats && Array.isArray(stats.level_summary) ? stats.level_summary : [];

  const rewardsSummary = rewardsData && rewardsData.summary ? rewardsData.summary : null;

  const totalStackCount =
    rewardsSummary && typeof rewardsSummary.total_stack_count === 'number'
      ? rewardsSummary.total_stack_count
      : 0;

  const totalInfluencerAmount = rewardsSummary
    ? rewardsSummary.total_influencer_amount
    : 0;

  const totalFirstTournamentAmount = rewardsSummary
    ? rewardsSummary.total_first_tournament_amount
    : 0;

  const totalDepositPercentAmount = rewardsSummary
    ? rewardsSummary.total_deposit_percent_amount
    : 0;

  const rewardsList = Array.isArray(rewardsData?.rewards)
    ? rewardsData.rewards
    : Array.isArray(rewardsData?.items)
    ? rewardsData.items
    : Array.isArray(rewardsData)
    ? rewardsData
    : [];

  const totalDepositsAmountRub =
    profileUser && profileUser.total_deposits !== null && typeof profileUser.total_deposits !== 'undefined'
      ? profileUser.total_deposits
      : '0.00';

  const profileDeposits =
    profileUser && Array.isArray(profileUser.deposits) ? profileUser.deposits : [];

  const totalInfluencerEarningsValue =
    profileUser && profileUser.total_influencer_earnings !== null && typeof profileUser.total_influencer_earnings !== 'undefined'
      ? profileUser.total_influencer_earnings
      : '0.00';

  const displayedInfluencerEarnings = totalInfluencerEarningsValue || '0.00';

  const isInfluencerProfile =
    backendUserType === 'influencer' ||
    Boolean(profileUser && profileUser.is_influencer) ||
    Number(totalInfluencerEarningsValue) > 0;

  const walletBalance =
    walletSummary && typeof walletSummary.balance !== 'undefined'
      ? walletSummary.balance
      : 0;

  const walletTotalDeposited =
    walletSummary && typeof walletSummary.total_deposited !== 'undefined'
      ? walletSummary.total_deposited
      : 0;

  const walletTotalSpent =
    walletSummary && typeof walletSummary.total_spent !== 'undefined'
      ? walletSummary.total_spent
      : 0;

  const referralBonusesTotalCalculated = referralBonuses.reduce((sum, bonus) => {
    const value = bonus && (typeof bonus.amount === 'string' || typeof bonus.amount === 'number')
      ? Number(bonus.amount)
      : 0;
    if (Number.isNaN(value)) {
      return sum;
    }
    return sum + value;
  }, 0);

  const totalReferralBonusesDisplay =
    referralTotalBonusesAmount || referralBonusesTotalCalculated;

  const referralDepositsTotalCalculated = referralDeposits.reduce((sum, item) => {
    const value = item && (typeof item.amount === 'string' || typeof item.amount === 'number')
      ? Number(item.amount)
      : 0;
    if (Number.isNaN(value)) {
      return sum;
    }
    return sum + value;
  }, 0);

  const totalReferralDepositsDisplay =
    referralTotalDepositsAmount || referralDepositsTotalCalculated;

  const sortedRankRules = Array.isArray(rankRules)
    ? [...rankRules].sort((a, b) => {
        const aVal = getSafeMultiplier(a && a.required_referrals, 0);
        const bVal = getSafeMultiplier(b && b.required_referrals, 0);
        return aVal - bVal;
      })
    : [];

  const currentRankRuleFromList = sortedRankRules.find((rule) => rule && rule.rank === rankCode) || null;

  const levelSummaryFromTree = (() => {
    if (!Array.isArray(treeData) || treeData.length === 0) {
      return [];
    }

    const map = new Map();

    treeData.forEach((node) => {
      if (!node) {
        return;
      }

      const levelRaw = node.level;
      const level =
        typeof levelRaw === 'number' && levelRaw > 0 ? levelRaw : 0;

      if (!level) {
        return;
      }

      const isActive = Boolean(node.is_active_referral || node.has_paid_first_bonus);

      const existing = map.get(level) || {
        level,
        totalReferrals: 0,
        activeReferrals: 0,
      };

      existing.totalReferrals += 1;
      if (isActive) {
        existing.activeReferrals += 1;
      }

      map.set(level, existing);
    });

    return Array.from(map.values()).sort((a, b) => a.level - b.level);
  })();

  const rewardDescriptionLines =
    backendUserType === 'influencer'
      ? getInfluencerRewardDescription(
          rankLabel,
          rankCode,
          sortedRankRules,
          currentRankRule,
        )
      : getPlayerRewardDescription(
          rankLabel,
          rankCode,
          sortedRankRules,
          currentRankRule,
        );

  const handleRetry = () => {
    loadProfile();
    loadStats();
    loadReferralTree();
    loadReferralRewards();
  };

  const handleSavePayoutDetails = async (event) => {
    if (event && event.preventDefault) {
      event.preventDefault();
    }

    setPayoutError('');
    setPayoutSuccess('');
    setIsSavingPayout(true);

    try {
      const payload = {
        withdrawal_bank_details: bankDetails || null,
        withdrawal_crypto_wallet: cryptoWallet || null,
      };

      const updatedMember = await updateProfile(payload);

      setProfileData(updatedMember || null);
      if (setMember) {
        setMember(updatedMember || null);
      }

      setPayoutSuccess('Реквизиты для вывода успешно сохранены.');
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      let message = 'Не удалось сохранить реквизиты. Попробуйте ещё раз.';

      if (err && err.response && err.response.data) {
        const data = err.response.data;
        if (typeof data.detail === 'string') {
          message = data.detail;
        } else if (typeof data.error === 'string') {
          message = data.error;
        }
      }

      setPayoutError(message);
    } finally {
      setIsSavingPayout(false);
    }
  };

  const handleSubmitWithdrawal = async (event) => {
    if (event && event.preventDefault) {
      event.preventDefault();
    }

    setWithdrawalError('');
    setWithdrawalSuccess('');

    const amountNumber = Number(withdrawalAmount);

    if (!withdrawalAmount || Number.isNaN(amountNumber) || amountNumber <= 0) {
      setWithdrawalError('Укажите корректную сумму для вывода больше 0.');
      return;
    }

    if (!withdrawalDestination) {
      setWithdrawalError('Укажите реквизиты для вывода (номер карты или адрес кошелька).');
      return;
    }

    setIsSubmittingWithdrawal(true);

    try {
      const payload = {
        amount: amountNumber,
        method: withdrawalMethod,
        destination: withdrawalDestination,
      };

      await createWithdrawalRequest(payload);

      setWithdrawalSuccess('Заявка на вывод успешно отправлена.');
      setWithdrawalAmount('');
      setWithdrawalDestination('');

      await loadWithdrawals();
    } catch (err) {
      const statusCode = err && err.response ? err.response.status : null;

      if (statusCode === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      let message = 'Не удалось отправить заявку на вывод. Попробуйте ещё раз.';

      if (err && err.response && err.response.data) {
        const data = err.response.data;
        if (typeof data.detail === 'string') {
          message = data.detail;
        } else if (typeof data.amount === 'string') {
          message = data.amount;
        }
      }

      setWithdrawalError(message);
    } finally {
      setIsSubmittingWithdrawal(false);
    }
  };

  const buildWalletErrorMessage = (error, defaultMessage, insufficientMessage) => {
    let message = defaultMessage;
    const response = error && error.response ? error.response : null;

    if (response && response.data) {
      const responseData = response.data;
      if (typeof responseData.detail === 'string') {
        message = responseData.detail;
      } else if (typeof responseData.error === 'string') {
        message = responseData.error;
      } else if (typeof responseData.message === 'string') {
        message = responseData.message;
      } else if (
        Array.isArray(responseData.non_field_errors) &&
        responseData.non_field_errors.length > 0
      ) {
        message = String(responseData.non_field_errors[0]);
      }
    }

    if (insufficientMessage && response && response.status === 400) {
      const responseData = response.data || {};

      if (responseData && responseData.code === 'insufficient_funds') {
        return insufficientMessage;
      }

      const parts = [];

      if (responseData && typeof responseData.detail === 'string') {
        parts.push(responseData.detail);
      }
      if (responseData && typeof responseData.error === 'string') {
        parts.push(responseData.error);
      }
      if (responseData && typeof responseData.message === 'string') {
        parts.push(responseData.message);
      }

      const combined = parts.join(' ').toLowerCase();

      if (
        combined.indexOf('insufficient') !== -1 ||
        combined.indexOf('недостаточно') !== -1
      ) {
        message = insufficientMessage;
      }
    }

    return message;
  };

  const handleWalletDepositSubmit = async (event) => {
    if (event && event.preventDefault) {
      event.preventDefault();
    }

    setWalletDepositError('');
    setWalletDepositSuccess('');

    const amountNumber = Number(walletDepositAmount);

    if (!walletDepositAmount || Number.isNaN(amountNumber) || amountNumber <= 0) {
      setWalletDepositError('Сумма должна быть положительным числом.');
      return;
    }

    setIsSubmittingDeposit(true);

    try {
      const payload = {
        amount: amountNumber,
      };

      if (walletDepositComment) {
        payload.description = walletDepositComment;
      }

      await createWalletDeposit(payload);

      setWalletDepositSuccess('Баланс успешно пополнен.');
      setWalletDepositAmount('');
      setWalletDepositComment('');

      await loadWalletSummary();
      await loadWalletTransactions(1);
    } catch (error) {
      const response = error && error.response ? error.response : null;

      if (response && response.status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      const message = buildWalletErrorMessage(
        error,
        'Не удалось пополнить баланс. Попробуйте ещё раз.',
        null,
      );

      setWalletDepositError(message);
    } finally {
      setIsSubmittingDeposit(false);
    }
  };

  const handleWalletPrevPage = () => {
    if (walletTransactionsLoading || !walletTransactionsHasPrev) {
      return;
    }

    const previousPage =
      walletTransactionsPage > 1 ? walletTransactionsPage - 1 : 1;
    loadWalletTransactions(previousPage);
  };

  const handleWalletNextPage = () => {
    if (walletTransactionsLoading || !walletTransactionsHasNext) {
      return;
    }

    const nextPage = walletTransactionsPage + 1;
    loadWalletTransactions(nextPage);
  };

  const formatRewardTypeLabel = (rewardType) => {
    if (rewardType === 'PLAYER_STACK') {
      return 'Бесплатный стартовый стек';
    }
    if (rewardType === 'INFLUENCER_FIRST_TOURNAMENT') {
      return 'Инфлюенсер: первый турнир реферала';
    }
    if (rewardType === 'INFLUENCER_DEPOSIT_PERCENT') {
      return 'Инфлюенсер: процент с депозитов';
    }
    if (!rewardType) {
      return 'Вознаграждение';
    }
    return 'Другое вознаграждение';
  };

  const formatRewardDateTime = (isoValue) => {
    if (!isoValue) {
      return '—';
    }

    try {
      const date = new Date(isoValue);
      if (Number.isNaN(date.getTime())) {
        return isoValue;
      }
      return date.toLocaleString('ru-RU');
    } catch (dateError) {
      return isoValue;
    }
  };

  const formatStackText = (count) => {
    if (!count) {
      return '';
    }

    if (count === 1) {
      return '1 стек';
    }

    if (count >= 2 && count <= 4) {
      return `${count} стека`;
    }

    return `${count} стеков`;
  };

  const formatWithdrawalMethodLabel = (method) => {
    if (method === 'crypto') {
      return 'Криптокошелёк';
    }
    if (method === 'card') {
      return 'Банковская карта';
    }
    return 'Способ вывода';
  };

  const formatWithdrawalStatusLabel = (status) => {
    if (status === 'pending') {
      return 'В обработке';
    }
    if (status === 'approved') {
      return 'Одобрена';
    }
    if (status === 'rejected') {
      return 'Отклонена';
    }
    if (status === 'paid') {
      return 'Выплачена';
    }
    return 'Статус неизвестен';
  };

  const formatTransactionTypeLabel = (type) => {
    if (type === 'deposit') {
      return 'Пополнение';
    }
    if (type === 'spend') {
      return 'Списание';
    }
    if (type === 'bonus') {
      return 'Бонус';
    }
    if (!type) {
      return 'Операция';
    }
    return 'Другая операция';
  };

  const handleChangePasswordSubmit = async (event) => {
    event.preventDefault();
    setChangePasswordErrors({});
    setChangePasswordSuccess('');

    if (!oldPassword || !newPassword) {
      setChangePasswordErrors({
        non_field_errors: 'Пожалуйста, заполните оба поля.',
      });
      return;
    }

    setIsChangingPassword(true);

    try {
      const payload = {
        old_password: oldPassword,
        new_password: newPassword,
      };

      const data = await changePassword(payload);
      const detailMessage = data && data.detail
        ? data.detail
        : 'Пароль успешно изменён.';

      setChangePasswordSuccess(detailMessage);
      setOldPassword('');
      setNewPassword('');
    } catch (error) {
      const responseData = error && error.response && error.response.data ? error.response.data : null;
      const nextErrors = {};

      if (responseData) {
        if (responseData.old_password) {
          const value = Array.isArray(responseData.old_password)
            ? responseData.old_password[0]
            : responseData.old_password;
          nextErrors.old_password = String(value);
        }
        if (responseData.new_password) {
          const value = Array.isArray(responseData.new_password)
            ? responseData.new_password[0]
            : responseData.new_password;
          nextErrors.new_password = String(value);
        }
        if (responseData.non_field_errors) {
          const value = Array.isArray(responseData.non_field_errors)
            ? responseData.non_field_errors[0]
            : responseData.non_field_errors;
          nextErrors.non_field_errors = String(value);
        }
        if (!nextErrors.non_field_errors && typeof responseData.detail === 'string') {
          nextErrors.non_field_errors = responseData.detail;
        }
      } else {
        nextErrors.non_field_errors = 'Не удалось изменить пароль. Попробуйте ещё раз.';
      }

      setChangePasswordErrors(nextErrors);
    } finally {
      setIsChangingPassword(false);
    }
  };

  return (
    <main
      data-easytag="id1-src/components/Profile/index.jsx"
      className="page page-profile"
    >
      <div className="container">
        <div className="profile-grid">
          <section className="card profile-header-card">
            <h1 className="page-title">Профиль пользователя</h1>
            <p className="page-subtitle">
              Ваш персональный кабинет участника реферальной программы покерного клуба.
              Здесь видно, какой у вас статус, какой ранг и сколько вы уже заработали.
            </p>

            <div className="profile-info-grid">
              <div className="profile-info-column">
                <div className="profile-info-row">
                  <div className="profile-label">Имя</div>
                  <div className="profile-value">
                    {profileUser && profileUser.first_name ? profileUser.first_name : '—'}
                  </div>
                </div>
                <div className="profile-info-row">
                  <div className="profile-label">Фамилия</div>
                  <div className="profile-value">
                    {profileUser && profileUser.last_name ? profileUser.last_name : '—'}
                  </div>
                </div>
              </div>

              <div className="profile-info-column">
                <div className="profile-info-row">
                  <div className="profile-label">Телефон</div>
                  <div className="profile-value">
                    {profileUser && profileUser.phone ? profileUser.phone : '—'}
                  </div>
                </div>
                <div className="profile-info-row">
                  <div className="profile-label">Email</div>
                  <div className="profile-value">
                    {profileUser && profileUser.email ? profileUser.email : '—'}
                  </div>
                </div>
              </div>

              <div className="profile-info-column">
                <div className="profile-info-row">
                  <div className="profile-label">Тип аккаунта</div>
                  <div className="profile-tag">{accountTypeLabel}</div>
                </div>
                <div className="profile-info-row">
                  <div className="profile-label">Текущий ранг</div>
                  <div className="profile-value">{rankLabel}</div>
                </div>
                <div className="profile-info-row">
                  <div className="profile-label">Прямые рефералы</div>
                  <div className="profile-value">
                    {directReferralsCount}{' '}
                    <span className="profile-inline-note">
                      (активных: {activeDirectReferralsCount})
                    </span>
                  </div>
                </div>
                {referralCode && (
                  <div className="profile-info-row">
                    <div className="profile-label">Реферальный код</div>
                    <div className="profile-value">{referralCode}</div>
                  </div>
                )}
              </div>
            </div>

            <div className="profile-balance-grid">
              <div className="profile-balance-card">
                <div className="profile-label">Баланс фишек (V-Coins)</div>
                <div className="profile-balance-value">{vCoinsBalance}</div>
                <div className="profile-stat-caption">
                  Виртуальные фишки, которые можно использовать для участия в турнирах и
                  внутриигровых бонусов.
                </div>
              </div>

              <div className="profile-balance-card">
                <div className="profile-label">Баланс в рублях</div>
                <div className="profile-balance-value">{`${cashBalance} ₽`}</div>
                <div className="profile-stat-caption">
                  Денежные вознаграждения (для инфлюенсеров), доступные для вывода по
                  правилам клуба.
                </div>
              </div>
            </div>

            {profileLoading && (
              <div className="profile-status-message">Обновление профиля...</div>
            )}
          </section>

          <section className="card profile-password-card">
            <h2 className="profile-section-title">Смена пароля</h2>
            <p className="profile-section-text">
              Для безопасности аккаунта регулярно обновляйте пароль. Новый пароль должен
              содержать не менее 6 символов.
            </p>

            <form className="profile-payout-form" onSubmit={handleChangePasswordSubmit}>
              <div className="profile-form-row">
                <label className="profile-label" htmlFor="oldPassword">
                  Текущий пароль
                </label>
                <input
                  id="oldPassword"
                  type="password"
                  className="profile-input"
                  value={oldPassword}
                  onChange={(event) => setOldPassword(event.target.value)}
                  placeholder="Введите текущий пароль"
                />
                {changePasswordErrors.old_password && (
                  <div className="profile-status-message profile-status-error">
                    {changePasswordErrors.old_password}
                  </div>
                )}
              </div>

              <div className="profile-form-row">
                <label className="profile-label" htmlFor="newPassword">
                  Новый пароль
                </label>
                <input
                  id="newPassword"
                  type="password"
                  className="profile-input"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="Минимум 6 символов"
                />
                {changePasswordErrors.new_password && (
                  <div className="profile-status-message profile-status-error">
                    {changePasswordErrors.new_password}
                  </div>
                )}
              </div>

              {changePasswordErrors.non_field_errors && (
                <div className="profile-status-message profile-status-error">
                  {changePasswordErrors.non_field_errors}
                </div>
              )}

              {changePasswordSuccess && (
                <div className="profile-status-message profile-status-success">
                  {changePasswordSuccess}
                </div>
              )}

              <div className="profile-form-actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isChangingPassword}
                >
                  {isChangingPassword ? 'Сохранение...' : 'Изменить пароль'}
                </button>
              </div>
            </form>
          </section>
        </div>

        <section className="card profile-wallet-card">
          <h2 className="profile-section-title">Кошелёк игрока</h2>
          <p className="profile-section-text">
            Внутренний кошелёк для учета средств внутри клуба. Вы можете пополнить баланс и
            видеть историю всех операций; списания и игровые траты выполняются
            администратором клуба и отображаются здесь автоматически.
          </p>

          {walletLoading && !walletError && (
            <div className="profile-wallet-status">Загрузка данных кошелька...</div>
          )}

          {walletError && (
            <div className="profile-status-message profile-status-error">
              {walletError}
            </div>
          )}

          {!walletError && (
            <>
              <div className="profile-wallet-summary-grid">
                <div className="profile-wallet-summary-card">
                  <div className="profile-stat-label">Текущий баланс</div>
                  <div className="profile-wallet-balance-value">{`${walletBalance} ₽`}</div>
                  <div className="profile-stat-caption">
                    Средства, доступные для отображения и контроля ваших игр в клубе.
                  </div>
                </div>

                <div className="profile-wallet-summary-card">
                  <div className="profile-stat-label">Всего пополнено</div>
                  <div className="profile-wallet-summary-value">{`${walletTotalDeposited} ₽`}</div>
                  <div className="profile-stat-caption">
                    Суммарная сумма всех пополнений кошелька за всё время.
                  </div>
                </div>

                <div className="profile-wallet-summary-card">
                  <div className="profile-stat-label">Всего списано</div>
                  <div className="profile-wallet-summary-value">{`${walletTotalSpent} ₽`}</div>
                  <div className="profile-stat-caption">
                    Сумма всех оплат и внутренних списаний из кошелька, проведённых
                    администратором клуба.
                  </div>
                </div>
              </div>

              <div className="profile-wallet-forms">
                <div className="profile-wallet-form">
                  <h3 className="profile-section-subtitle">Пополнить баланс</h3>
                  <p className="profile-wallet-inline-help">
                    Введите сумму пополнения и при необходимости комментарий. Пополнение
                    производится в рублях.
                  </p>

                  <form
                    className="profile-wallet-form-inner"
                    onSubmit={handleWalletDepositSubmit}
                  >
                    <div className="profile-form-row">
                      <label className="profile-label" htmlFor="walletDepositAmount">
                        Сумма (₽)
                      </label>
                      <input
                        id="walletDepositAmount"
                        type="number"
                        min="0"
                        step="0.01"
                        className="profile-input"
                        value={walletDepositAmount}
                        onChange={(event) => setWalletDepositAmount(event.target.value)}
                        placeholder="Например: 500"
                      />
                    </div>

                    <div className="profile-form-row">
                      <label className="profile-label" htmlFor="walletDepositComment">
                        Комментарий (опционально)
                      </label>
                      <textarea
                        id="walletDepositComment"
                        className="profile-textarea"
                        rows={2}
                        value={walletDepositComment}
                        onChange={(event) => setWalletDepositComment(event.target.value)}
                        placeholder="Например: пополнение перед игрой"
                      />
                    </div>

                    {walletDepositError && (
                      <div className="profile-status-message profile-status-error">
                        {walletDepositError}
                      </div>
                    )}

                    {walletDepositSuccess && (
                      <div className="profile-status-message profile-status-success">
                        {walletDepositSuccess}
                      </div>
                    )}

                    <div className="profile-form-actions">
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={isSubmittingDeposit}
                      >
                        {isSubmittingDeposit ? 'Обработка...' : 'Пополнить баланс'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              <div className="profile-wallet-transactions">
                <h3 className="profile-section-subtitle">История операций</h3>

                {walletTransactionsLoading && (
                  <div className="profile-wallet-status">
                    Загрузка истории операций...
                  </div>
                )}

                {walletTransactionsError && !walletTransactionsLoading && (
                  <div className="profile-status-message profile-status-error">
                    {walletTransactionsError}
                  </div>
                )}

                {!walletTransactionsLoading && !walletTransactionsError && (
                  walletTransactions.length === 0 ? (
                    <div className="profile-history-empty">
                      Операции с кошельком пока не выполнялись.
                    </div>
                  ) : (
                    <>
                      <div className="profile-history-table-wrapper">
                        <table className="profile-history-table">
                          <thead>
                            <tr>
                              <th>Дата</th>
                              <th>Тип операции</th>
                              <th>Сумма</th>
                              <th>Описание</th>
                            </tr>
                          </thead>
                          <tbody>
                            {walletTransactions.map((transaction, index) => {
                              const key = transaction.id || index;
                              const typeLabel = formatTransactionTypeLabel(
                                transaction.type,
                              );

                              const amountValue =
                                typeof transaction.amount === 'number' ||
                                typeof transaction.amount === 'string'
                                  ? transaction.amount
                                  : 0;

                              let amountText = `${amountValue} ₽`;

                              if (transaction.type === 'spend' && amountValue > 0) {
                                amountText = `-${amountValue} ₽`;
                              }
                              if (transaction.type === 'deposit' && amountValue > 0) {
                                amountText = `+${amountValue} ₽`;
                              }

                              const descriptionText =
                                transaction.description || transaction.comment || '—';

                              const dateText = formatRewardDateTime(
                                transaction.created_at || transaction.date,
                              );

                              return (
                                <tr key={key}>
                                  <td>{dateText}</td>
                                  <td>{typeLabel}</td>
                                  <td>{amountText}</td>
                                  <td>{descriptionText}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      <div className="profile-wallet-transactions-pagination">
                        <span>
                          Страница {walletTransactionsPage}
                          {walletTransactionsTotalCount
                            ? ` • Всего операций: ${walletTransactionsTotalCount}`
                            : ''}
                        </span>
                        <div className="profile-wallet-transactions-pagination-actions">
                          <button
                            type="button"
                            className="btn btn-outline"
                            onClick={handleWalletPrevPage}
                            disabled={
                              !walletTransactionsHasPrev || walletTransactionsLoading
                            }
                          >
                            Предыдущая
                          </button>
                          <button
                            type="button"
                            className="btn btn-outline"
                            onClick={handleWalletNextPage}
                            disabled={
                              !walletTransactionsHasNext || walletTransactionsLoading
                            }
                          >
                            Следующая
                          </button>
                        </div>
                      </div>
                    </>
                  )
                )}
              </div>
            </>
          )}
        </section>

        <section className="card profile-referral-card">
          <h2 className="profile-section-title">Реферальная программа</h2>
          <p className="profile-section-text">
            Делитесь персональной ссылкой, приглашайте новых игроков в офлайн покерный
            клуб и получайте вознаграждения в глубину всей вашей структуры.
          </p>

          <div className="profile-referral-block">
            <div className="profile-label">Ваша реферальная ссылка</div>
            <div className="profile-referral-input-row">
              <input
                type="text"
                readOnly
                value={referralLink}
                className="profile-referral-input"
              />
              <button
                type="button"
                className="btn btn-primary profile-referral-copy-btn"
                onClick={() => handleCopyLink(referralLink)}
                disabled={!referralLink}
              >
                Скопировать
              </button>
            </div>

            {copyStatus && <div className="profile-copy-status">{copyStatus}</div>}
          </div>

          <ul className="profile-rules-list">
            <li>
              Вы получаете 1 бесплатный стартовый стек (1000 ₽ участие в турнире) за
              каждого нового игрока, который впервые приходит в клуб по вашей ссылке.
            </li>
            <li>
              Если ваш реферал приглашает новых игроков, вы также получаете свои бонусы
              по всей цепочке до максимальной глубины программы.
            </li>
          </ul>
        </section>

        <section className="card profile-rank-info-card">
          <h2 className="profile-section-title">Ваш ранг и правила вознаграждений</h2>
          <p className="profile-section-text">
            Размер глубинного кэшбэка и бонусов зависит от типа аккаунта и текущего ранга.
          </p>
          <ul className="profile-rank-rules-list">
            {rewardDescriptionLines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>

          {rankRulesLoading && !rankRulesError && (
            <div className="profile-status-message">Загрузка параметров рангов...</div>
          )}

          {rankRulesError && (
            <div className="profile-status-message profile-status-error">
              {rankRulesError}
            </div>
          )}

          {!rankRulesLoading && sortedRankRules.length > 0 && (
            <div className="profile-rank-table-wrapper">
              <h3 className="profile-section-subtitle">Все ранги и требования</h3>
              <table className="profile-rank-table">
                <thead>
                  <tr>
                    <th>Ранг</th>
                    <th>Активные рефералы 1-го уровня</th>
                    <th>Глубинный бонус для игроков</th>
                    <th>Глубинный бонус для инфлюенсеров</th>
                    <th>До следующего ранга</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRankRules.map((rule, index) => {
                    if (!rule) {
                      return null;
                    }

                    const ruleRank = rule.rank || 'standard';
                    const isCurrent = ruleRank === rankCode;

                    const requiredReferrals = getSafeMultiplier(
                      rule.required_referrals,
                      0,
                    );

                    const playerMultiplier = getSafeMultiplier(
                      rule.player_depth_bonus_multiplier,
                      1,
                    );
                    const influencerMultiplier = getSafeMultiplier(
                      rule.influencer_depth_bonus_multiplier,
                      1,
                    );

                    const playerDepthBonus = 100 * playerMultiplier;
                    const influencerDepthBonus = 50 * influencerMultiplier;

                    const nextRule = sortedRankRules[index + 1] || null;

                    let toNextText = 'Максимальный ранг';
                    if (nextRule && nextRule.rank) {
                      const nextRequired = getSafeMultiplier(
                        nextRule.required_referrals,
                        0,
                      );
                      const diff = nextRequired - activeDirectReferralsCount;
                      if (diff <= 0) {
                        toNextText = `Вы уже выполняете требование следующего ранга (${getRankLabel(
                          nextRule.rank,
                        )}).`;
                      } else {
                        toNextText = `Осталось ${diff} активных прямых рефералов до ранга ${getRankLabel(
                          nextRule.rank,
                        )}.`;
                      }
                    }

                    return (
                      <tr
                        key={rule.rank || index}
                        className={isCurrent ? 'profile-rank-row-current' : ''}
                      >
                        <td>{getRankLabel(ruleRank)}</td>
                        <td>{requiredReferrals}</td>
                        <td>{`${playerDepthBonus} V-Coins`}</td>
                        <td>{`${influencerDepthBonus} ₽`}</td>
                        <td>{toNextText}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {isInfluencerProfile && (
          <section className="card profile-influencer-earnings-card">
            <h2 className="profile-section-title">Заработано как инфлюенсер</h2>
            <p className="profile-section-text">
              Общая сумма заработка от депозитов и активности приглашённых вами игроков во
              всей структуре.
            </p>

            <div className="profile-balance-grid">
              <div className="profile-balance-card profile-balance-card-accent">
                <div className="profile-label">Заработано денег</div>
                <div className="profile-balance-value profile-balance-value-large">
                  {`${displayedInfluencerEarnings} ₽`}
                </div>
                <div className="profile-stat-caption">
                  Сюда входят бонусы за первые турниры и процент с депозитов ваших рефералов
                  по всей структуре.
                </div>
              </div>
            </div>
          </section>
        )}

        {backendUserType === 'influencer' && (
          <section className="card profile-payout-card">
            <h2 className="profile-section-title">Реквизиты для вывода средств</h2>
            <p className="profile-section-text">
              Укажите реквизиты банковской карты или криптокошелька, куда клуб будет
              переводить ваши денежные вознаграждения как инфлюенсера.
            </p>

            <form className="profile-payout-form" onSubmit={handleSavePayoutDetails}>
              <div className="profile-form-row">
                <label className="profile-label" htmlFor="bankDetails">
                  Банковская карта / счёт
                </label>
                <textarea
                  id="bankDetails"
                  className="profile-textarea"
                  value={bankDetails}
                  onChange={(event) => setBankDetails(event.target.value)}
                  placeholder="Например: номер карты, банк, ФИО получателя"
                  rows={3}
                />
              </div>

              <div className="profile-form-row">
                <label className="profile-label" htmlFor="cryptoWallet">
                  Криптокошелёк
                </label>
                <textarea
                  id="cryptoWallet"
                  className="profile-textarea"
                  value={cryptoWallet}
                  onChange={(event) => setCryptoWallet(event.target.value)}
                  placeholder="Например: адрес USDT (TRC-20) или другого токена"
                  rows={3}
                />
              </div>

              {payoutError && (
                <div className="profile-status-message profile-status-error">
                  {payoutError}
                </div>
              )}

              {payoutSuccess && (
                <div className="profile-status-message profile-status-success">
                  {payoutSuccess}
                </div>
              )}

              <div className="profile-form-actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSavingPayout}
                >
                  {isSavingPayout ? 'Сохранение...' : 'Сохранить реквизиты'}
                </button>
              </div>
            </form>
          </section>
        )}

        {backendUserType === 'influencer' && (
          <section className="card profile-withdraw-card">
            <h2 className="profile-section-title">Вывести деньги</h2>
            <p className="profile-section-text">
              Оформите заявку на вывод части заработанных средств на банковскую карту или
              криптокошелёк. Максимальная сумма зависит от доступного для вывода баланса.
            </p>

            <form className="profile-payout-form" onSubmit={handleSubmitWithdrawal}>
              <div className="profile-form-row">
                <div className="profile-label">Способ вывода</div>
                <div className="profile-radio-group">
                  <label className="profile-radio-item">
                    <input
                      type="radio"
                      name="withdrawMethod"
                      value="card"
                      checked={withdrawalMethod === 'card'}
                      onChange={() => setWithdrawalMethod('card')}
                    />
                    <span>Банковская карта</span>
                  </label>
                  <label className="profile-radio-item">
                    <input
                      type="radio"
                      name="withdrawMethod"
                      value="crypto"
                      checked={withdrawalMethod === 'crypto'}
                      onChange={() => setWithdrawalMethod('crypto')}
                    />
                    <span>Криптокошелёк</span>
                  </label>
                </div>
              </div>

              <div className="profile-form-row">
                <label className="profile-label" htmlFor="withdrawDestination">
                  Реквизиты для вывода
                </label>
                <input
                  id="withdrawDestination"
                  type="text"
                  className="profile-input"
                  value={withdrawalDestination}
                  onChange={(event) => setWithdrawalDestination(event.target.value)}
                  placeholder={
                    withdrawalMethod === 'crypto'
                      ? 'Адрес криптокошелька'
                      : 'Номер банковской карты'
                  }
                />
              </div>

              <div className="profile-form-row">
                <label className="profile-label" htmlFor="withdrawAmount">
                  Сумма для вывода (₽)
                </label>
                <input
                  id="withdrawAmount"
                  type="number"
                  min="0"
                  step="0.01"
                  className="profile-input"
                  value={withdrawalAmount}
                  onChange={(event) => setWithdrawalAmount(event.target.value)}
                  placeholder="Например: 1000"
                />
              </div>

              {withdrawalError && (
                <div className="profile-status-message profile-status-error">
                  {withdrawalError}
                </div>
              )}

              {withdrawalSuccess && (
                <div className="profile-status-message profile-status-success">
                  {withdrawalSuccess}
                </div>
              )}

              <div className="profile-form-actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmittingWithdrawal}
                >
                  {isSubmittingWithdrawal ? 'Отправка...' : 'Отправить заявку'}
                </button>
              </div>
            </form>

            <div className="profile-withdraw-history">
              <h3 className="profile-section-subtitle">История заявок на вывод</h3>

              {isLoadingWithdrawals && (
                <div className="profile-status-message">Загрузка заявок...</div>
              )}

              {withdrawalsError && !isLoadingWithdrawals && (
                <div className="profile-status-message profile-status-error">
                  {withdrawalsError}
                </div>
              )}

              {!isLoadingWithdrawals && !withdrawalsError && (
                withdrawals.length === 0 ? (
                  <div className="profile-withdraw-empty">
                    Заявок на вывод пока нет.
                  </div>
                ) : (
                  <div className="profile-withdraw-table-wrapper">
                    <table className="profile-withdraw-table">
                      <thead>
                        <tr>
                          <th>Сумма</th>
                          <th>Метод</th>
                          <th>Реквизиты</th>
                          <th>Статус</th>
                          <th>Дата</th>
                        </tr>
                      </thead>
                      <tbody>
                        {withdrawals.map((item, index) => {
                          const key = item.id || index;
                          const amountText =
                            typeof item.amount === 'number' || typeof item.amount === 'string'
                              ? `${item.amount} ₽`
                              : '—';

                          const methodLabel = formatWithdrawalMethodLabel(item.method);
                          const statusLabel = formatWithdrawalStatusLabel(item.status);
                          const dateText = formatRewardDateTime(item.created_at);

                          return (
                            <tr key={key}>
                              <td>{amountText}</td>
                              <td>{methodLabel}</td>
                              <td>{item.destination || '—'}</td>
                              <td>{statusLabel}</td>
                              <td>{dateText}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )
              )}
            </div>
          </section>
        )}

        {loading && (
          <div className="profile-status-message">Загрузка статистики...</div>
        )}

        {!loading && error && (
          <div className="profile-status-message profile-status-error">
            <span>{error}</span>
            <button
              type="button"
              className="btn btn-outline profile-retry-btn"
              onClick={handleRetry}
            >
              Повторить попытку
            </button>
          </div>
        )}

        <section className="profile-stats-section">
          <div className="profile-stats-grid">
            <div className="card profile-stat-card">
              <div className="profile-stat-label">Количество рефералов</div>
              <div className="profile-stat-value">{totalReferrals}</div>
              <div className="profile-stat-caption">
                Все игроки, которые впервые пришли в покерный клуб по вашей ссылке или
                ссылкам ваших рефералов.
              </div>
              <div className="profile-stat-caption">
                Прямых рефералов: {directReferralsCount}, активных прямых: {activeDirectReferralsCount}.
              </div>
            </div>

            <div className="card profile-stat-card">
              <div className="profile-stat-label">Активные рефералы (30 дней)</div>
              <div className="profile-stat-value">{activeReferrals}</div>
              <div className="profile-stat-caption">
                Рефералы, которые посещали клуб или делали депозиты на фишки за последние 30
                дней.
              </div>
            </div>

            <div className="card profile-stat-card">
              <div className="profile-stat-label">Бесплатные стартовые стеки</div>
              <div className="profile-stat-value">{totalBonusPoints}</div>
              <div className="profile-stat-caption">
                Каждый бонус = один бесплатный стартовый стек (1000 ₽ участие в турнире).
              </div>
            </div>

            {backendUserType === 'influencer' && (
              <div className="card profile-stat-card profile-stat-card-accent">
                <div className="profile-stat-label">Заработано денег</div>
                <div className="profile-stat-value">{`${totalMoneyEarned} ₽`}</div>
                <div className="profile-stat-caption">
                  500 ₽ за первый турнир прямых рефералов + 10% с последующих депозитов на
                  фишки по вашей структуре, с учётом глубинного кэшбэка по рангу.
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="card profile-deposits-card">
          <div className="profile-deposits-header">
            <h2 className="profile-section-title">Депозиты</h2>
            <p className="profile-section-text">
              Здесь отображаются все зафиксированные депозиты на фишки для вашего профиля.
            </p>
          </div>

          <div className="profile-deposits-summary">
            <p className="profile-deposits-summary-line">
              Всего депозитов: <strong>{`${totalDepositsAmountRub} ₽`}</strong>
            </p>
          </div>

          {profileDeposits.length === 0 ? (
            <div className="profile-deposits-empty">
              У вас пока нет зафиксированных депозитов на фишки.
            </div>
          ) : (
            <div className="profile-deposits-table-wrapper">
              <table className="profile-deposits-table">
                <thead>
                  <tr>
                    <th>Сумма</th>
                    <th>Валюта</th>
                    <th>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {profileDeposits.map((deposit) => {
                    const key = deposit.id || deposit.created_at || deposit.amount;

                    const amountText =
                      typeof deposit.amount === 'number' || typeof deposit.amount === 'string'
                        ? `${deposit.amount} ₽`
                        : '—';

                    const currencyText = deposit.currency || 'RUB';
                    const dateText = formatRewardDateTime(deposit.created_at);

                    return (
                      <tr key={key}>
                        <td>{amountText}</td>
                        <td>{currencyText}</td>
                        <td>{dateText}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {myDepositsCount > 0 && (
            <div className="profile-deposits-legacy-note">
              <div className="profile-stat-caption">
                Для обратной совместимости система также хранит агрегированную историю
                депозитов, используемую в реферальной статистике: {myDepositsCount}{' '}
                операций на сумму {myDepositsTotalAmount} ₽.
              </div>
            </div>
          )}
        </section>

        <section className="card profile-tree-card">
          <div className="profile-tree-header">
            <h2 className="profile-section-title">Моя структура рефералов</h2>
            <p className="profile-section-text">
              Список всех игроков в вашей реферальной структуре с указанием уровня и
              статуса активации каждого реферала.
            </p>
          </div>

          {levelSummaryFromTree.length > 0 && (
            <div className="profile-level-summary">
              <h3 className="profile-section-subtitle">Сводка по уровням глубины</h3>
              <table className="profile-level-summary-table">
                <thead>
                  <tr>
                    <th>Уровень</th>
                    <th>Всего рефералов</th>
                    <th>Активных</th>
                  </tr>
                </thead>
                <tbody>
                  {levelSummaryFromTree.map((row) => (
                    <tr key={row.level}>
                      <td>{row.level}</td>
                      <td>{row.totalReferrals}</td>
                      <td>{row.activeReferrals}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {levelSummaryFromStats.length > 0 && levelSummaryFromTree.length === 0 && (
            <div className="profile-level-summary">
              <h3 className="profile-section-subtitle">Сводка по уровням глубины</h3>
              <table className="profile-level-summary-table">
                <thead>
                  <tr>
                    <th>Уровень</th>
                    <th>Всего рефералов</th>
                    <th>Активных</th>
                  </tr>
                </thead>
                <tbody>
                  {levelSummaryFromStats.map((row) => (
                    <tr key={row.level}>
                      <td>{row.level}</td>
                      <td>{row.total_referrals}</td>
                      <td>{row.active_referrals}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {isLoadingTree && (
            <div className="profile-tree-loading">Загрузка структуры...</div>
          )}

          {treeError && !isLoadingTree && (
            <div className="profile-tree-error">{treeError}</div>
          )}

          {!isLoadingTree && !treeError && (
            treeData.length === 0 ? (
              <div className="profile-tree-empty">
                У вас пока нет рефералов. Поделитесь реферальной ссылкой, чтобы начать
                строить структуру.
              </div>
            ) : (
              <div className="profile-tree-table-wrapper">
                <table className="profile-tree-table">
                  <thead>
                    <tr>
                      <th>Пользователь</th>
                      <th>Тип</th>
                      <th>Ранг</th>
                      <th>Уровень</th>
                      <th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {treeData.map((node, index) => {
                      const displayName = node && node.username
                        ? node.username
                        : node && node.descendant_id
                        ? `ID ${node.descendant_id}`
                        : '-';

                      const level =
                        typeof node.level === 'number' && node.level > 0 ? node.level : 0;

                      const nodeUserType = node && node.user_type ? node.user_type : 'player';
                      const nodeTypeLabel = getUserTypeLabel(nodeUserType);

                      const nodeRankLabel = getRankLabel(node && node.rank ? node.rank : 'standard');

                      const isActive = Boolean(
                        (node && node.is_active_referral) || (node && node.has_paid_first_bonus)
                      );

                      return (
                        <tr key={node.descendant_id || index}>
                          <td>{displayName}</td>
                          <td>{nodeTypeLabel}</td>
                          <td>{nodeRankLabel}</td>
                          <td>{level}</td>
                          <td>{isActive ? 'Активный реферал' : 'Неактивный'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          )}
        </section>

        <section className="card profile-rewards-card">
          <div className="profile-rewards-header">
            <h2 className="profile-section-title">Мои вознаграждения</h2>
            <p className="profile-section-text">
              Сводка бесплатных стартовых стеков и денежных вознаграждений, которые вы
              получили как игрок или инфлюенсер за всю глубину вашей структуры.
            </p>
          </div>

          <div className="profile-rewards-summary-grid">
            <div className="profile-rewards-summary-card">
              <div className="profile-stat-label">Бесплатные стартовые стеки</div>
              <div className="profile-stat-value">{totalStackCount}</div>
              <div className="profile-stat-caption">
                Суммарное количество стеков, начисленных за новых игроков в вашей структуре.
              </div>
            </div>

            <div className="profile-rewards-summary-card">
              <div className="profile-stat-label">Сумма вознаграждений как инфлюенсера</div>
              <div className="profile-stat-value">{`${totalInfluencerAmount} ₽`}</div>
              <div className="profile-stat-caption">
                Если у вас статус инфлюенсера, сюда входят все денежные выплаты по
                структуре.
              </div>
            </div>

            {Number(totalFirstTournamentAmount) > 0 && (
              <div className="profile-rewards-summary-card">
                <div className="profile-stat-label">За первые турниры рефералов</div>
                <div className="profile-stat-value">
                  {`${totalFirstTournamentAmount} ₽`}
                </div>
                <div className="profile-stat-caption">
                  Сумма 500/1000 ₽ за первый турнир каждого приведённого игрока по правилам
                  для игроков и инфлюенсеров.
                </div>
              </div>
            )}

            {Number(totalDepositPercentAmount) > 0 && (
              <div className="profile-rewards-summary-card">
                <div className="profile-stat-label">Процент с депозитов на фишки</div>
                <div className="profile-stat-value">
                  {`${totalDepositPercentAmount} ₽`}
                </div>
                <div className="profile-stat-caption">
                  10% со всех дальнейших депозитов на фишки ваших прямых рефералов.
                </div>
              </div>
            )}
          </div>

          {isLoadingRewards && (
            <div className="profile-rewards-loading">Загрузка вознаграждений...</div>
          )}

          {rewardsError && !isLoadingRewards && (
            <div className="profile-rewards-error">{rewardsError}</div>
          )}

          {!isLoadingRewards && !rewardsError && (
            rewardsList.length === 0 ? (
              <div className="profile-rewards-empty">
                Пока нет начисленных вознаграждений. Приглашайте новых игроков, чтобы
                получать бесплатные стеки и денежные бонусы.
              </div>
            ) : (
              <div className="profile-rewards-table-wrapper">
                <table className="profile-rewards-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Тип</th>
                      <th>От кого</th>
                      <th>Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rewardsList.map((reward, index) => {
                      const key = reward.id || index;

                      const sourceName =
                        reward && reward.source_member_name
                          ? reward.source_member_name
                          : reward && reward.source_member_full_name
                          ? reward.source_member_full_name
                          : reward && reward.referred_name
                          ? reward.referred_name
                          : '-';

                      const amountRub =
                        typeof reward.amount_rub === 'number'
                          ? reward.amount_rub
                          : reward && typeof reward.amount_rub === 'string'
                          ? Number(reward.amount_rub) || 0
                          : 0;

                      const stackCount =
                        typeof reward.stack_count === 'number'
                          ? reward.stack_count
                          : reward && typeof reward.stack_count === 'string'
                          ? Number(reward.stack_count) || 0
                          : 0;

                      let amountText = '—';

                      if (amountRub) {
                        amountText = `${amountRub} ₽`;
                      } else if (stackCount) {
                        amountText = formatStackText(stackCount);
                      }

                      return (
                        <tr key={key}>
                          <td>{formatRewardDateTime(reward.created_at || reward.date)}</td>
                          <td>{formatRewardTypeLabel(reward.reward_type)}</td>
                          <td>{sourceName}</td>
                          <td>{amountText}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          )}
        </section>

        <section className="card profile-referral-bonuses-card">
          <h2 className="profile-section-title">Реферальные бонусы</h2>
          <p className="profile-section-text">
            Здесь отображаются бонусы, которые вы получили за списания средств из кошельков
            ваших рефералов. Данные обновляются автоматически с небольшим интервалом.
          </p>

          <div className="profile-deposits-summary">
            <p className="profile-deposits-summary-line">
              Всего бонусов за траты рефералов:{' '}
              <strong>{`${totalReferralBonusesDisplay} ₽`}</strong>
            </p>
          </div>

          {referralBonusesLoading && (
            <div className="profile-status-message">Загрузка реферальных бонусов...</div>
          )}

          {referralBonusesError && !referralBonusesLoading && (
            <div className="profile-status-message profile-status-error">
              {referralBonusesError}
            </div>
          )}

          {!referralBonusesLoading && !referralBonusesError && (
            referralBonuses.length === 0 ? (
              <div className="profile-history-empty">
                Бонусы за траты рефералов пока не начислялись.
              </div>
            ) : (
              <div className="profile-deposits-table-wrapper">
                <table className="profile-deposits-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Реферал</th>
                      <th>Сумма бонуса</th>
                      <th>Исходная трата</th>
                    </tr>
                  </thead>
                  <tbody>
                    {referralBonuses.map((bonus, index) => {
                      const key = bonus.id || index;
                      const referred = bonus.referred_member || {};

                      const fullNameParts = [];
                      if (referred.first_name) {
                        fullNameParts.push(referred.first_name);
                      }
                      if (referred.last_name) {
                        fullNameParts.push(referred.last_name);
                      }
                      const fullName = fullNameParts.join(' ');
                      const phone = referred.phone || '';
                      const referralDisplay = fullName || phone || 'Реферал';

                      const amountValue =
                        typeof bonus.amount === 'number' || typeof bonus.amount === 'string'
                          ? bonus.amount
                          : 0;

                      const spendAmountValue =
                        bonus.spend_amount &&
                        (typeof bonus.spend_amount === 'number' ||
                          typeof bonus.spend_amount === 'string')
                          ? bonus.spend_amount
                          : 0;

                      const amountText = `${amountValue} ₽`;
                      const spendText = spendAmountValue
                        ? `${spendAmountValue} ₽`
                        : '—';

                      const dateText = formatRewardDateTime(bonus.created_at);

                      return (
                        <tr key={key}>
                          <td>{dateText}</td>
                          <td>{referralDisplay}</td>
                          <td>{amountText}</td>
                          <td>{spendText}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          )}
        </section>

        <section className="card profile-referral-deposits-card">
          <h2 className="profile-section-title">Депозиты ваших рефералов</h2>
          <p className="profile-section-text">
            Список депозитов на фишки, которые совершили ваши прямые рефералы. Эти данные
            помогают отслеживать активность структуры и начисление процентных бонусов.
          </p>

          <div className="profile-deposits-summary">
            <p className="profile-deposits-summary-line">
              Всего депозитов рефералов:{' '}
              <strong>{`${totalReferralDepositsDisplay} ₽`}</strong>
            </p>
          </div>

          {referralDepositsLoading && (
            <div className="profile-status-message">Загрузка депозитов рефералов...</div>
          )}

          {referralDepositsError && !referralDepositsLoading && (
            <div className="profile-status-message profile-status-error">
              {referralDepositsError}
            </div>
          )}

          {!referralDepositsLoading && !referralDepositsError && (
            referralDeposits.length === 0 ? (
              <div className="profile-deposits-empty">
                Ваши рефералы пока не совершали депозитов.
              </div>
            ) : (
              <div className="profile-deposits-table-wrapper">
                <table className="profile-deposits-table">
                  <thead>
                    <tr>
                      <th>Реферал</th>
                      <th>Сумма депозита</th>
                      <th>Валюта</th>
                      <th>Дата</th>
                    </tr>
                  </thead>
                  <tbody>
                    {referralDeposits.map((deposit, index) => {
                      const key = deposit.id || index;
                      const referred = deposit.member || {};

                      const fullNameParts = [];
                      if (referred.first_name) {
                        fullNameParts.push(referred.first_name);
                      }
                      if (referred.last_name) {
                        fullNameParts.push(referred.last_name);
                      }
                      const fullName = fullNameParts.join(' ');
                      const phone = referred.phone || '';
                      const referralDisplay = fullName || phone || 'Реферал';

                      const amountText =
                        typeof deposit.amount === 'number' || typeof deposit.amount === 'string'
                          ? `${deposit.amount} ₽`
                          : '—';

                      const currencyText = deposit.currency || 'RUB';
                      const dateText = formatRewardDateTime(deposit.created_at);

                      return (
                        <tr key={key}>
                          <td>{referralDisplay}</td>
                          <td>{amountText}</td>
                          <td>{currencyText}</td>
                          <td>{dateText}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          )}
        </section>

        <section className="card profile-chart-card">
          <div className="profile-chart-header">
            <h2 className="profile-section-title">График регистраций</h2>
            <p className="profile-section-text">
              Динамика привлечения новых игроков по вашей реферальной ссылке и структуре.
            </p>
          </div>

          <div className="profile-chart-inner">
            {chartData.length === 0 ? (
              <div className="profile-chart-empty">
                Пока нет данных для отображения графика.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.35)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#e5e7eb' }}
                    stroke="rgba(148, 163, 184, 0.7)"
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: '#e5e7eb' }}
                    stroke="rgba(148, 163, 184, 0.7)"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#020617',
                      borderRadius: '0.75rem',
                      border: '1px solid rgba(148, 163, 184, 0.6)',
                      color: '#e5e7eb',
                      fontSize: '0.85rem',
                    }}
                    labelStyle={{ color: '#f9fafb', marginBottom: 4 }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: 8 }}
                    iconType="circle"
                    formatter={(value) => (
                      <span style={{ color: '#e5e7eb', fontSize: '0.85rem' }}>
                        {value === 'count' ? 'Регистрации' : value}
                      </span>
                    )}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    name="Регистрации"
                    stroke="#60a5fa"
                    strokeWidth={2.4}
                    dot={{
                      r: 4,
                      strokeWidth: 2,
                      stroke: '#1d4ed8',
                      fill: '#0ea5e9',
                    }}
                    activeDot={{
                      r: 6,
                      strokeWidth: 0,
                      fill: '#fb7185',
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="card profile-history-card">
          <div className="profile-history-header">
            <h2 className="profile-section-title">История начислений</h2>
            <p className="profile-section-text">
              Дополнительная история бонусов и выплат по вашим рефералам, включающая
              бесплатные стеки и денежные вознаграждения.
            </p>
          </div>

          {history.length === 0 ? (
            <div className="profile-history-empty">
              Пока нет начислений. Поделитесь реферальной ссылкой, чтобы начать
              зарабатывать.
            </div>
          ) : (
            <div className="profile-history-table-wrapper">
              <table className="profile-history-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Реферал</th>
                    <th>Бонусы</th>
                    <th>Деньги</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((entry, index) => {
                    const referralName =
                      entry && entry.referred_name
                        ? entry.referred_name
                        : entry && entry.referred_full_name
                        ? entry.referred_full_name
                        : '-';

                    const bonus =
                      typeof entry.bonus_amount === 'number'
                        ? entry.bonus_amount
                        : entry.bonus_amount || 0;

                    const money =
                      typeof entry.money_amount === 'number'
                        ? entry.money_amount
                        : entry.money_amount || 0;

                    return (
                      <tr key={entry.id || index}>
                        <td>{entry.date || '—'}</td>
                        <td>{referralName}</td>
                        <td>{bonus}</td>
                        <td>{money ? `${money} ₽` : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
};

export default ProfilePage;
