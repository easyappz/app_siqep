import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
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
} from '../../api/referrals';
import { createWithdrawalRequest, getMyWithdrawalRequests } from '../../api/withdrawals';
import { changePassword } from '../../api/auth';
import {
  getWalletSummary,
  getWalletTransactions,
  createWalletDeposit,
  createWalletSpend,
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

function getPlayerRewardDescription(rankLabel, currentRankRule) {
  const multiplier = currentRankRule
    ? Number(currentRankRule.player_depth_bonus_multiplier || 1)
    : 1;

  const baseDepth = 100;
  const depthBonus = baseDepth * multiplier;

  const depthBonusText = `${depthBonus} V-Coins`;

  return [
    `Ваш текущий ранг: ${rankLabel}.`,
    'За каждого прямого реферала, который впервые приходит в клуб и играет первый платный турнир, вы получаете 1000 V-Coins (эквивалент стартового стека).',
    `За рефералов на уровнях 2–10 вы получаете глубинный кэшбэк: ${depthBonusText} за первый турнир каждого игрока в цепочке (множитель относительно базовых 100 V-Coins зависит от ранга).`,
  ];
}

function getInfluencerRewardDescription(rankLabel, currentRankRule) {
  const multiplier = currentRankRule
    ? Number(currentRankRule.influencer_depth_bonus_multiplier || 1)
    : 1;

  const baseDirect = 500;
  const baseDepth = 50;
  const depthBonus = baseDepth * multiplier;

  const depthBonusText = `${depthBonus} ₽`;

  return [
    `Ваш текущий ранг: ${rankLabel}.`,
    `За прямого реферала (уровень 1) вы получаете ${baseDirect} ₽ за его первый турнир.`,
    `За рефералов на уровнях 2–10 вы получаете глубинный кэшбэк: ${depthBonusText} за первый турнир каждого нового игрока в цепочке (множитель относительно базовых 50 ₽ зависит от ранга).`,
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

  const [rewardsData, setRewardsData] = useState({ rewards: [], summary: null });
  const [isLoadingRewards, setIsLoadingRewards] = useState(false);
  const [rewardsError, setRewardsError] = useState('');

  const [bankDetails, setBankDetails] = useState('');
  const [cryptoWallet, setCryptoWallet] = useState('');
  const [isSavingPayout, setIsSavingPayout] = useState(false);
  const [payoutError, setPayoutError] = useState('');
  the [payoutSuccess, setPayoutSuccess] = useState('');

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

  const [walletSpendAmount, setWalletSpendAmount] = useState('');
  const [walletSpendDescription, setWalletSpendDescription] = useState('');
  const [walletSpendCategory, setWalletSpendCategory] = useState('');
  const [walletSpendError, setWalletSpendError] = useState('');
  const [walletSpendSuccess, setWalletSpendSuccess] = useState('');
  const [isSubmittingSpend, setIsSubmittingSpend] = useState(false);

  const [referralBonuses, setReferralBonuses] = useState([]);
  const [referralBonusesLoading, setReferralBonusesLoading] = useState(false);
  const [referralBonusesError, setReferralBonusesError] = useState('');

  const [referralDeposits, setReferralDeposits] = useState([]);
  const [referralDepositsLoading, setReferralDepositsLoading] = useState(false);
  const [referralDepositsError, setReferralDepositsError] = useState('');

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

  // ... (continued with remaining original component code updated accordingly)
