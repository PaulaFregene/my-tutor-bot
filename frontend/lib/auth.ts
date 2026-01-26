import { useUser } from "@clerk/nextjs";

export const useAnonUserId = () => {
    const { user } = useUser();
    return user?.id; //unique per user
};

export const useUsername = () => {
    const { user } = useUser();
    return user?.username || "";
};

export const isAdmin = (userId: string) => {
    const adminIds = ["my_clerk_user_id_here"];
    return adminIds.includes(userId);
};