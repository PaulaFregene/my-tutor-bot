import { useUser } from "@clerk/nextjs";

export const useAnonUserId = () => {
  const { user } = useUser();
  return user?.id; //unique per user
};

export const useUsername = () => {
  const { user } = useUser();
  return user?.username || "";
};

export const useIsAdmin = () => {
  const { user } = useUser();
  // Check if user has admin role in publicMetadata
  return user?.publicMetadata?.role === "admin";
};
