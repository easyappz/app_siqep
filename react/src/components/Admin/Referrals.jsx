import React, { useEffect, useState } from 'react';
import {
  fetchAdminReferrals,
  createAdminReferralEvent,
  fetchAdminMembers,
} from '../../api/admin';
import { fetchReferralTree, fetchReferralRewards } from '../../api/referrals';
import { useAuth } from '../../context/AuthContext';

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

const AdminReferralsPage = () => {
  const { member } = useAuth();

  const [referrals, setReferrals] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [typeFilter, setTypeFilter] = useState('all');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const [createReferredId, setCreateReferredId] = useState('');
  const [createDepositAmount, setCreateDepositAmount] = useState('1000');
  const [createDateTime, setCreateDateTime] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');

  const [memberSearchQuery, setMemberSearchQuery] = useState('');
  const [memberSearchResults, setMemberSearchResults] = useState([]);
  const [memberSearchLoading, setMemberSearchLoading] = useState(false);
  const [memberSearchError, setMemberSearchError] = useState('');
  const [selectedMemberId, setSelectedMemberId] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);

  const [memberTreeData, setMemberTreeData] = useState([]);
  const [memberTreeLoading, setMemberTreeLoading] = useState(false);
  const [memberTreeError, setMemberTreeError] = useState('');

  const [memberRewardsData, setMemberRewardsData] = useState(null);
  const [memberRewardsLoading, setMemberRewardsLoading] = useState(false);
  const [memberRewardsError, setMemberRewardsError] = useState('');

  const loadReferrals = async (pageParam, options) => {
    setLoading(true);
    setError('');

    try {
      const params = { page: pageParam };

      if (options && options.typeFilter) {
        if (options.typeFilter === 'influencers') {
          params.is_influencer = true;
        }
        if (options.typeFilter === 'regular') {
          params.is_influencer = false;
        }
      }

      if (options && options.fromDate) {
        params.from_date = options.fromDate;
      }

      if (options && options.toDate) {
        params.to_date = options.toDate;
      }

      const data = await fetchAdminReferrals(params);
      const results = Array.isArray(data.results) ? data.results : [];

      setReferrals(results);
      setCount(typeof data.count === 'number' ? data.count : results.length);

      const pageSize = results.length > 0 ? results.length : 1;
      const pages = data.count ? Math.max(1, Math.ceil(data.count / pageSize)) : 1;
      setTotalPages(pages);
    } catch (err) {
      console.error('Failed to load admin referrals', err);
      setError('Не удалось загрузить реферальные события. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReferrals(page, { typeFilter, fromDate, toDate });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, typeFilter, fromDate, toDate]);

  const handleTypeFilterChange = (event) => {
    setPage(1);
    setTypeFilter(event.target.value);
  };

  const handleFromDateChange = (event) => {
    setPage(1);
    setFromDate(event.target.value);
  };

  const handleToDateChange = (event) => {
    setPage(1);
    setToDate(event.target.value);
  };

  const handlePrevPage = ()n  ... (file content truncated for brevity) ...